// Package chat implements the conversation viewport for aiw-tui.
package chat

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/glamour"

	"aiw-tui/theme"
	"aiw-tui/types"
)

// Model is the chat conversation component.
type Model struct {
	Messages       []types.Message
	Viewport       viewport.Model
	Ready          bool
	CurrentStream  *StreamState
	ShowToolCalls  bool // collapsed or expanded
	Width          int
	Height         int
	glamourRenderer *glamour.TermRenderer
}

// StreamState tracks an in-progress streaming response.
type StreamState struct {
	Buffer    strings.Builder
	AccumText string
	Done      bool
	MsgIndex  int // index in Messages of the streaming message
}

// New creates a new chat model with the default theme.
func New(width, height int) Model {
	renderer, err := glamour.NewTermRenderer(
		glamour.WithAutoStyle(),
		glamour.WithWordWrap(width - 4),
	)
	if err != nil {
		// Fallback: renderer will be nil, renderMessage handles it
		renderer = nil
	}

	vp := viewport.New(width, height-2)
	vp.Style = theme.AppStyle
	vp.YPosition = 0

	return Model{
		Messages:        []types.Message{},
		Viewport:        vp,
		ShowToolCalls:   true,
		Width:           width,
		Height:          height,
		glamourRenderer: renderer,
	}
}

// Init initializes the chat model.
func (m Model) Init() tea.Cmd {
	return nil
}

// Update handles messages for the chat model.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.Width = msg.Width
		m.Height = msg.Height
		m.Viewport.Width = msg.Width
		m.Viewport.Height = msg.Height - 2
		if !m.Ready {
			m.Viewport.YPosition = 0
			m.Ready = true
		}
		// Recreate glamour renderer with new width
		if r, err := glamour.NewTermRenderer(
			glamour.WithAutoStyle(),
			glamour.WithWordWrap(msg.Width-4),
		); err == nil {
			m.glamourRenderer = r
		}
		// If glamour fails, keep the old renderer (or nil)

	case tea.KeyMsg:
		switch msg.String() {
		case "pgup":
			m.Viewport.HalfViewUp()
		case "pgdown":
			m.Viewport.HalfViewDown()
		case "home":
			m.Viewport.GotoTop()
		case "end":
			m.Viewport.GotoBottom()
		}
	}

	return m, nil
}

// View renders the chat conversation.
func (m Model) View() string {
	if !m.Ready {
		return ""
	}

	var rendered []string
	for _, msg := range m.Messages {
		rendered = append(rendered, m.renderMessage(msg))
	}

	content := strings.Join(rendered, "\n")
	m.Viewport.SetContent(content)
	m.Viewport.GotoBottom()

	return m.Viewport.View()
}

func (m Model) renderMessage(msg types.Message) string {
	switch msg.Type {
	case types.MsgUser:
		return theme.UserMsgStyle.Render(fmt.Sprintf("▸ %s", msg.Content))

	case types.MsgAssistant:
		if m.glamourRenderer != nil {
			rendered, err := m.glamourRenderer.Render(msg.Content)
			if err == nil {
				return strings.TrimRight(rendered, "\n")
			}
		}
		// Fallback: plain text without markdown
		return theme.AssistantMsgStyle.Render(msg.Content)

	case types.MsgThinking:
		if msg.Step > 0 {
			return theme.ThinkingStyle.Render(fmt.Sprintf("Step %d: %s", msg.Step, msg.Content))
		}
		return theme.ThinkingStyle.Render(msg.Content)

	case types.MsgToolCall:
		args := formatArgs(msg.ToolArgs)
		header := fmt.Sprintf("🔧 %s(%s)", msg.ToolName, truncate(args, 80))
		return theme.ToolCallHeader.Render(header)

	case types.MsgToolResult:
		lines := strings.Count(msg.Content, "\n") + 1
		preview := truncate(msg.Content, 200)
		return theme.ToolResultBody.Render(fmt.Sprintf("  ▼ result (%d lines):\n  %s", lines, preview))

	case types.MsgError:
		return theme.ErrorStyle.Render(fmt.Sprintf("✗ %s", msg.Content))

	case types.MsgSystem:
		return theme.SystemStyle.Render(msg.Content)

	default:
		return msg.Content
	}
}

// ── Actions ─────────────────────────────────────────────────────────

// AddUserMessage adds a user message to the conversation.
func (m *Model) AddUserMessage(text string) {
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgUser,
		Content: text,
	})
}

// AddAssistantMessage adds an assistant message (non-streaming).
func (m *Model) AddAssistantMessage(text string) {
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgAssistant,
		Content: text,
	})
}

// StartStreaming begins a new streaming assistant response.
func (m *Model) StartStreaming() {
	idx := len(m.Messages)
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgAssistant,
		Content: "",
	})
	m.CurrentStream = &StreamState{
		MsgIndex: idx,
	}
}

// AppendToken appends a token to the current streaming response.
func (m *Model) AppendToken(text string) {
	if m.CurrentStream == nil || m.CurrentStream.Done {
		return
	}
	m.CurrentStream.Buffer.WriteString(text)
	m.CurrentStream.AccumText = m.CurrentStream.Buffer.String()
	m.Messages[m.CurrentStream.MsgIndex].Content = m.CurrentStream.AccumText
}

// FinalizeStream marks the current stream as complete.
func (m *Model) FinalizeStream() {
	if m.CurrentStream != nil {
		m.CurrentStream.Done = true
		m.CurrentStream = nil
	}
}

// AddThinking adds a thinking step message.
func (m *Model) AddThinking(text string, step int) {
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgThinking,
		Content: text,
		Step:    step,
	})
}

// AddToolCall adds a tool call message.
func (m *Model) AddToolCall(name string, args map[string]any, id string) {
	m.Messages = append(m.Messages, types.Message{
		Type:     types.MsgToolCall,
		ToolName: name,
		ToolArgs: args,
		ToolID:   id,
	})
}

// AddToolResult adds a tool result message.
func (m *Model) AddToolResult(id, result string) {
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgToolResult,
		ToolID:  id,
		Content: result,
	})
}

// AddError adds an error message.
func (m *Model) AddError(text string) {
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgError,
		Content: text,
	})
}

// AddSystem adds a system message.
func (m *Model) AddSystem(text string) {
	m.Messages = append(m.Messages, types.Message{
		Type:    types.MsgSystem,
		Content: text,
	})
}

// Clear removes all messages.
func (m *Model) Clear() {
	m.Messages = nil
	m.CurrentStream = nil
}

// ── Helpers ─────────────────────────────────────────────────────────

func formatArgs(args map[string]any) string {
	if args == nil {
		return ""
	}
	parts := make([]string, 0, len(args))
	for k, v := range args {
		parts = append(parts, fmt.Sprintf("%s=%v", k, v))
	}
	return strings.Join(parts, ", ")
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "..."
}