// Package app is the main Bubble Tea application model.
package app

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"aiw-tui/chat"
	"aiw-tui/input"
	"aiw-tui/ipc"
	"aiw-tui/statusbar"
	"aiw-tui/theme"
	"aiw-tui/types"
)

// Screen represents the active screen/overlay.
type Screen int

const (
	ScreenChat Screen = iota
	ScreenHelp
	ScreenDashboard
	ScreenSessions
	ScreenContext
	ScreenGit
	ScreenFileBrowser
)

// ── Messages ──────────────────────────────────────────────────────────

// BackendEventMsg wraps a backend IPC event for the tea event loop.
type BackendEventMsg struct {
	Event *types.Event
}

// BackendDoneMsg signals the backend process has exited.
type BackendDoneMsg struct {
	Err error
}

// StartEventReaderMsg is send on Init to start the IPC reader goroutine.
type StartEventReaderMsg struct{}

// ── Model ─────────────────────────────────────────────────────────────

// Model is the main application model.
type Model struct {
	IPC    *ipc.Client

	// Sub-models
	Chat      chat.Model
	Input     input.Model
	StatusBar statusbar.Model

	// State
	Screen       Screen
	Width        int
	Height       int
	ModelName    string
	SessionID    string
	AgentRunning bool
	TaskHistory  []string

	// IPC event channel
	events chan *types.Event

	// Cached data from non-streaming commands
	dashboardData   *types.DashboardData
	contextData     *types.ContextData
	gitData         *types.GitData
	sessionsData    []types.SessionSummary
	fileBrowserData *types.FileBrowserData

	// Quick help viewport for scrolling
	helpViewport viewport.Model
}

// New creates a new application model.
func New(client *ipc.Client, width, height int) Model {
	helpVP := viewport.New(width-4, height-6)
	helpVP.Style = theme.AppStyle

	return Model{
		IPC:          client,
		Chat:         chat.New(width, height-3),
		Input:        input.New(width),
		StatusBar:    statusbar.New(),
		Screen:       ScreenChat,
		Width:        width,
		Height:       height,
		ModelName:    "qwen3:14b",
		SessionID:    "new",
		events:       make(chan *types.Event, 100),
		helpViewport: helpVP,
	}
}

// Init initializes the application and starts the IPC reader.
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		m.Chat.Init(),
		m.Input.Init(),
		func() tea.Msg {
			return StartEventReaderMsg{}
		},
	)
}

// startEventReader spawns a goroutine that reads IPC events into the channel.
func startEventReader(client *ipc.Client, events chan<- *types.Event, done chan<- BackendDoneMsg) {
	for {
		event, err := client.ReadEvent()
		if err != nil {
			done <- BackendDoneMsg{Err: err}
			close(events)
			return
		}
		events <- event
	}
}

// pollEvents returns a tea.Cmd that checks for events from the channel.
func (m Model) pollEvents() tea.Msg {
	select {
	case event := <-m.events:
		if event == nil {
			return nil
		}
		return BackendEventMsg{Event: event}
	default:
		return nil
	}
}

// Update handles all messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.Width = msg.Width
		m.Height = msg.Height
		m.Chat.Width = msg.Width
		m.Chat.Height = msg.Height - 3
		m.Input.Width = msg.Width
		m.StatusBar.Width = msg.Width

		m.helpViewport.Width = msg.Width - 4
		m.helpViewport.Height = msg.Height - 6

	case StartEventReaderMsg:
		done := make(chan BackendDoneMsg, 1)
		go startEventReader(m.IPC, m.events, done)
		cmds = append(cmds, m.pollEvents, func() tea.Msg {
			return <-done
		})

	case BackendEventMsg:
		cmds = append(cmds, m.handleBackendEvent(msg.Event))

	case BackendDoneMsg:
		return m, tea.Quit

	case tea.KeyMsg:
		keyCmds := m.handleKeyMsg(msg)
		cmds = append(cmds, keyCmds...)
	}

	// Always poll for new events
	cmds = append(cmds, m.pollEvents)

	// Update sub-models
	chatModel, chatCmd := m.Chat.Update(msg)
	m.Chat = chatModel
	cmds = append(cmds, chatCmd)

	inputModel, inputCmd := m.Input.Update(msg)
	m.Input = inputModel
	cmds = append(cmds, inputCmd)

	return m, tea.Batch(cmds...)
}

// handleKeyMsg processes keyboard input.
func (m Model) handleKeyMsg(msg tea.KeyMsg) []tea.Cmd {
	var cmds []tea.Cmd

	switch msg.String() {
	case "ctrl+c":
		if m.AgentRunning {
			return []tea.Cmd{m.sendCommand(types.Command{Cmd: "cancel"})}
		}
		return []tea.Cmd{tea.Quit}

	case "esc":
		if m.Screen != ScreenChat {
			m.Screen = ScreenChat
			return nil
		}
		if m.AgentRunning {
			return []tea.Cmd{m.sendCommand(types.Command{Cmd: "cancel"})}
		}
		m.Input.Focus()

	case "enter":
		return m.handleEnter()

	case "f1":
		m.toggleScreen(ScreenHelp)

	case "f3":
		if m.toggleScreen(ScreenDashboard) {
			return []tea.Cmd{m.sendCommand(types.Command{Cmd: "dashboard"})}
		}

	case "f4":
		if m.toggleScreen(ScreenContext) {
			return []tea.Cmd{m.sendCommand(types.Command{Cmd: "context", Action: "list"})}
		}

	case "f5":
		m.refreshScreen()

	case "pgup":
		m.helpViewport.HalfViewUp()

	case "pgdown":
		m.helpViewport.HalfViewDown()

	case "r":
		if m.Screen == ScreenDashboard {
			return []tea.Cmd{m.sendCommand(types.Command{Cmd: "dashboard"})}
		}
		if m.Screen == ScreenGit {
			return []tea.Cmd{m.sendCommand(types.Command{Cmd: "git"})}
		}

	default:
		if m.Screen == ScreenChat {
			inputModel, _ := m.Input.Update(msg)
			m.Input = inputModel
		}
	}

	return cmds
}

// toggleScreen toggles to/from a screen. Returns true if a command should be sent.
func (m *Model) toggleScreen(s Screen) bool {
	if m.Screen == s {
		m.Screen = ScreenChat
		return false
	}
	m.Screen = s
	return true
}

// refreshScreen re-requests data for the current screen.
func (m *Model) refreshScreen() {
	switch m.Screen {
	case ScreenDashboard:
		m.dashboardData = nil
	case ScreenContext:
		m.contextData = nil
	case ScreenGit:
		m.gitData = nil
	case ScreenSessions:
		m.sessionsData = nil
	}
}

// handleEnter processes the Enter key (submit text or trigger autocomplete).
func (m Model) handleEnter() []tea.Cmd {
	text := m.Input.Value()
	if text == "" {
		return nil
	}

	// Check for slash commands
	if m.Input.IsSlashCommand(text) {
		cmd, args := m.Input.ParseCommand(text)
		return m.handleSlashCommand(cmd, args)
	}

	// Regular chat — ignore if agent is already running
	if m.AgentRunning {
		return nil
	}

	m.Input.SetValue("")
	m.TaskHistory = append(m.TaskHistory, text)
	m.Chat.AddUserMessage(text)

	return []tea.Cmd{
		m.sendCommand(types.Command{
			Cmd:   "chat",
			Task:  text,
			Model: m.ModelName,
		}),
	}
}

// handleSlashCommand processes a slash command.
func (m Model) handleSlashCommand(cmd, args string) []tea.Cmd {
	m.Input.SetValue("")

	switch cmd {
	case "/help":
		m.Screen = ScreenHelp
		return nil

	case "/clear":
		m.Chat.Clear()
		m.Screen = ScreenChat
		return nil

	case "/model":
		if args != "" {
			m.ModelName = args
			m.Chat.AddSystem(fmt.Sprintf("Switched model to %s", args))
		}
		return nil

	case "/sessions":
		m.Screen = ScreenSessions
		return []tea.Cmd{m.sendCommand(types.Command{Cmd: "sessions", Action: "list"})}

	case "/dashboard":
		m.Screen = ScreenDashboard
		return []tea.Cmd{m.sendCommand(types.Command{Cmd: "dashboard"})}

	case "/ctx":
		m.Screen = ScreenContext
		return []tea.Cmd{m.sendCommand(types.Command{Cmd: "context", Action: "list"})}

	case "/git":
		m.Screen = ScreenGit
		return []tea.Cmd{m.sendCommand(types.Command{Cmd: "git"})}

	case "/cost":
		m.Screen = ScreenDashboard
		return []tea.Cmd{m.sendCommand(types.Command{Cmd: "dashboard"})}

	case "/quit":
		return []tea.Cmd{tea.Quit}

	default:
		return nil
	}
}

// handleBackendEvent routes an IPC event to the appropriate handler.
func (m *Model) handleBackendEvent(event *types.Event) tea.Cmd {
	switch event.Type {
	case "token":
		var data types.TokenData
		if err := json.Unmarshal(event.Data, &data); err != nil {
			return nil
		}
		if m.Chat.CurrentStream == nil {
			m.Chat.StartStreaming()
			m.AgentRunning = true
		}
		m.Chat.AppendToken(data.Text)

	case "thinking":
		var data types.ThinkingData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		m.Chat.AddThinking(data.Text, 0)

	case "tool_call":
		var data types.ToolCallData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		if m.Chat.CurrentStream != nil {
			m.Chat.FinalizeStream()
		}
		m.Chat.AddToolCall(data.Name, data.Args, data.ID)

	case "tool_result":
		var data types.ToolResultData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		m.Chat.AddToolResult(data.ID, data.Result)

	case "done":
		var data types.DoneData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		if m.Chat.CurrentStream != nil {
			m.Chat.FinalizeStream()
		}
		m.AgentRunning = false
		m.StatusBar.Update(statusbar.State{
			Model:     m.ModelName,
			Tokens:    data.Tokens,
			Cost:      data.Cost,
			Running:   false,
			SessionID: m.SessionID,
		})

	case "error":
		var data types.ErrorData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		m.Chat.AddError(data.Message)

	case "phase":
		var data types.PhaseData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		if data.Phase != "" {
			m.Chat.AddThinking(fmt.Sprintf("Phase: %s", data.Phase), 0)
		}

	case "result":
		m.handleResult(event.Data)

	case "status":
		var data types.StatusData
		if json.Unmarshal(event.Data, &data) != nil {
			return nil
		}
		m.AgentRunning = data.Running
		m.StatusBar.Update(statusbar.State{
			Model:     m.ModelName,
			Tokens:    data.Tokens,
			Cost:      data.Cost,
			Running:   data.Running,
			SessionID: m.SessionID,
		})
	}

	return nil
}

// handleResult processes non-streaming result data.
func (m *Model) handleResult(raw json.RawMessage) {
	switch m.Screen {
	case ScreenDashboard:
		var db types.DashboardData
		if json.Unmarshal(raw, &db) == nil {
			m.dashboardData = &db
		}

	case ScreenSessions:
		var wrapper struct {
			Sessions []types.SessionSummary `json:"sessions"`
		}
		if json.Unmarshal(raw, &wrapper) == nil {
			m.sessionsData = wrapper.Sessions
		}

	case ScreenGit:
		var g types.GitData
		if json.Unmarshal(raw, &g) == nil {
			m.gitData = &g
		}

	case ScreenContext:
		var c types.ContextData
		if json.Unmarshal(raw, &c) == nil {
			m.contextData = &c
		}

	case ScreenFileBrowser:
		var fb types.FileBrowserData
		if json.Unmarshal(raw, &fb) == nil {
			m.fileBrowserData = &fb
		}
	}
}

// sendCommand sends a JSON command to the backend via IPC.
func (m Model) sendCommand(cmd types.Command) tea.Cmd {
	return func() tea.Msg {
		if err := m.IPC.Send(cmd); err != nil {
			return BackendDoneMsg{Err: fmt.Errorf("ipc send: %w", err)}
		}
		return nil
	}
}

// View renders the complete application.
func (m Model) View() string {
	var b strings.Builder

	switch m.Screen {
	case ScreenHelp:
		b.WriteString(m.Input.HelpView())
	case ScreenDashboard:
		b.WriteString(m.renderDashboard())
	case ScreenSessions:
		b.WriteString(m.renderSessions())
	case ScreenContext:
		b.WriteString(m.renderContext())
	case ScreenGit:
		b.WriteString(m.renderGit())
	case ScreenFileBrowser:
		b.WriteString(m.renderFileBrowser())
	default:
		b.WriteString(m.Chat.View())
	}

	b.WriteString("\n")
	b.WriteString(m.Input.View())
	b.WriteString("\n")
	b.WriteString(m.StatusBar.View())

	return b.String()
}

// ── Screen Renderers ──────────────────────────────────────────────────

func (m Model) renderDashboard() string {
	if m.dashboardData == nil {
		return "Loading dashboard..."
	}

	var b strings.Builder
	b.WriteString(theme.DashboardTitle.Render("Dashboard"))
	b.WriteString("\n\n")

	b.WriteString(theme.StatLabel.Render("Stats:"))
	b.WriteString("\n")
	if m.dashboardData.Stats != nil {
		for k, v := range m.dashboardData.Stats {
			b.WriteString(fmt.Sprintf("  %s: %v\n", k, v))
		}
	}

	b.WriteString("\n")
	b.WriteString(theme.StatLabel.Render("Health:"))
	b.WriteString("\n")
	if m.dashboardData.Health != nil {
		for k, v := range m.dashboardData.Health {
			color := theme.Success
			if s, ok := v.(string); ok && s != "ok" {
				color = theme.Error
			}
			b.WriteString(fmt.Sprintf("  %s: %s\n", k, lipgloss.NewStyle().Foreground(color).Render(fmt.Sprintf("%v", v))))
		}
	}

	b.WriteString("\n")
	b.WriteString(theme.StatLabel.Render("Cost:"))
	b.WriteString("\n")
	if m.dashboardData.Cost != nil {
		for k, v := range m.dashboardData.Cost {
			b.WriteString(fmt.Sprintf("  %s: %v\n", k, v))
		}
	}

	b.WriteString("\n")
	b.WriteString(theme.HelpDesc.Render("F3/ESC: close  •  F5: refresh  •  r: refresh"))
	return b.String()
}

func (m Model) renderSessions() string {
	if m.sessionsData == nil {
		return "Loading sessions..."
	}

	var b strings.Builder
	b.WriteString(theme.DashboardTitle.Render("Sessions"))
	b.WriteString("\n\n")

	if len(m.sessionsData) == 0 {
		b.WriteString("No saved sessions.")
		return b.String()
	}

	b.WriteString(fmt.Sprintf("%-14s %-12s %s\n",
		theme.ContextTokens.Render("ID"),
		theme.StatLabel.Render("Model"),
		"Summary",
	))
	b.WriteString(strings.Repeat("─", m.Width-4) + "\n")

	for _, s := range m.sessionsData {
		b.WriteString(fmt.Sprintf("%-14s %-12s %s\n",
			theme.ContextTokens.Render(s.ID[:min(len(s.ID), 12)]),
			theme.StatLabel.Render(s.Model),
			theme.FileStyle.Render(truncate(s.Summary, 40)),
		))
	}

	b.WriteString("\n")
	b.WriteString(theme.HelpDesc.Render("F5: refresh  •  ESC: back"))
	return b.String()
}

func (m Model) renderContext() string {
	if m.contextData == nil {
		return "Loading context..."
	}

	var b strings.Builder
	b.WriteString(theme.DashboardTitle.Render(fmt.Sprintf("Context Inspector  (%d tokens)", m.contextData.TotalTokens)))
	b.WriteString("\n\n")

	if len(m.contextData.Files) == 0 {
		b.WriteString("No files in context.")
		return b.String()
	}

	for _, f := range m.contextData.Files {
		var statusColor = theme.Success
		switch f.Status {
		case "drift":
			statusColor = theme.Warning
		case "stale":
			statusColor = theme.Error
		case "pinned":
			statusColor = theme.Primary
		}

		b.WriteString(theme.ContextPath.Render(truncate(f.Path, 38)))
		b.WriteString(" ")
		_ = statusColor // used for status label coloring
		b.WriteString(theme.ContextTokens.Render(fmt.Sprintf("%4d t", f.Tokens)))
		b.WriteString(fmt.Sprintf(" %6s", f.Status))
		b.WriteString(fmt.Sprintf(" %4d ln", f.Lines))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(theme.HelpDesc.Render("F4/ESC: close  •  F5: refresh"))
	return b.String()
}

func (m Model) renderGit() string {
	if m.gitData == nil {
		return "Loading git status..."
	}

	var b strings.Builder
	b.WriteString(theme.DashboardTitle.Render("Git Status"))
	b.WriteString("\n\n")

	b.WriteString("  ")
	b.WriteString(theme.GitBranch.Render(m.gitData.Branch))
	b.WriteString("\n\n")

	if len(m.gitData.Status) == 0 {
		b.WriteString("  Clean working tree\n")
	} else {
		for _, e := range m.gitData.Status {
			var entryStyle = theme.GitChanged
			switch e.Flag {
			case "M", "MM":
				entryStyle = theme.GitChanged
			case "A":
				entryStyle = theme.GitAdded
			case "?":
				entryStyle = theme.GitUntracked
			}
			b.WriteString(fmt.Sprintf("  %s ", entryStyle.Render(e.Flag)))
			b.WriteString(entryStyle.Render(e.Path))
			b.WriteString("\n")
		}
	}

	if len(m.gitData.Log) > 0 {
		b.WriteString("\n")
		b.WriteString(theme.GitBranch.Render("  Recent commits"))
		b.WriteString("\n")
		for _, c := range m.gitData.Log {
			hash := c.Hash
			if len(hash) > 7 {
				hash = hash[:7]
			}
			b.WriteString(fmt.Sprintf("  %s  %s\n",
				theme.ContextTokens.Render(hash),
				truncate(c.Message, 50),
			))
		}
	}

	b.WriteString("\n")
	b.WriteString(theme.HelpDesc.Render("F5: refresh  •  r: refresh  •  ESC: back"))
	return b.String()
}

func (m Model) renderFileBrowser() string {
	if m.fileBrowserData == nil {
		return "Loading..."
	}

	var b strings.Builder
	b.WriteString(theme.DashboardTitle.Render(m.fileBrowserData.Current))
	b.WriteString("\n\n")

	if m.fileBrowserData.Error != "" {
		b.WriteString(theme.ErrorStyle.Render(m.fileBrowserData.Error))
		return b.String()
	}

	if len(m.fileBrowserData.Entries) == 0 {
		b.WriteString("  (empty directory)")
	}

	for _, e := range m.fileBrowserData.Entries {
		if e.IsDir {
			b.WriteString("  ")
			b.WriteString(theme.DirStyle.Render("📁 " + e.Name))
			b.WriteString("\n")
		}
	}

	for _, e := range m.fileBrowserData.Entries {
		if !e.IsDir {
			b.WriteString("  ")
			b.WriteString(theme.FileStyle.Render(e.Name))
			b.WriteString("  ")
			b.WriteString(lipgloss.NewStyle().Foreground(theme.Faint).Render(formatSize(e.Size)))
			b.WriteString("\n")
		}
	}

	b.WriteString("\n")
	b.WriteString(theme.HelpDesc.Render("ESC: back"))
	return b.String()
}

// ── Helpers ───────────────────────────────────────────────────────────

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "..."
}

func formatSize(size int64) string {
	if size < 1024 {
		return fmt.Sprintf("%d B", size)
	} else if size < 1024*1024 {
		return fmt.Sprintf("%.1f KB", float64(size)/1024)
	}
	return fmt.Sprintf("%.1f MB", float64(size)/(1024*1024))
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}