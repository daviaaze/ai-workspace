// Package input implements the task input with slash command support.
package input

import (
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"aiw-tui/theme"
)

// SlashHandler is a function that handles a slash command.
type SlashHandler func(args string) tea.Cmd

// SlashCommand defines a slash command and its handler.
type SlashCommand struct {
	Desc    string
	Handler SlashHandler
}

// Model is the input component.
type Model struct {
	Input       textinput.Model
	Commands    map[string]SlashCommand
	Autocomplete []string
	ShowHelp    bool
	Width       int
}

// New creates a new input model.
func New(width int) Model {
	ti := textinput.New()
	ti.Placeholder = "Type a task or /help for commands..."
	ti.Prompt = "❯ "
	ti.TextStyle = lipgloss.NewStyle().Foreground(theme.Text)
	ti.PlaceholderStyle = lipgloss.NewStyle().Foreground(theme.Faint)
	ti.PromptStyle = lipgloss.NewStyle().Foreground(theme.Primary)
	ti.Cursor.Style = lipgloss.NewStyle().Foreground(theme.Accent)
	ti.Width = width - 4
	ti.Focus()

	commands := map[string]SlashCommand{
		"/help":      {Desc: "Show command reference", Handler: nil},
		"/model":     {Desc: "Switch model (e.g. /model qwen3:14b)", Handler: nil},
		"/clear":     {Desc: "Clear conversation", Handler: nil},
		"/sessions":  {Desc: "List and manage saved sessions", Handler: nil},
		"/export":    {Desc: "Export current session to text", Handler: nil},
		"/cost":      {Desc: "Show budget and cache stats", Handler: nil},
		"/git":       {Desc: "Show git status", Handler: nil},
		"/ctx":       {Desc: "Open context inspector", Handler: nil},
		"/dashboard": {Desc: "Show dashboard", Handler: nil},
		"/quit":      {Desc: "Exit", Handler: nil},
	}

	autocomplete := make([]string, 0, len(commands))
	for cmd := range commands {
		autocomplete = append(autocomplete, cmd)
	}

	return Model{
		Input:       ti,
		Commands:    commands,
		Autocomplete: autocomplete,
		Width:       width,
	}
}

// Init initializes the input model.
func (m Model) Init() tea.Cmd {
	return textinput.Blink
}

// Update handles messages for the input model.
func (m Model) Update(msg tea.Msg) (Model, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "tab":
			m.cycleAutocomplete()
		case "esc":
			m.Input.Blur()
			return m, nil
		}

	case tea.WindowSizeMsg:
		m.Width = msg.Width
		m.Input.Width = msg.Width - 4
	}

	m.Input, cmd = m.Input.Update(msg)
	return m, cmd
}

// View renders the input component.
func (m Model) View() string {
	return m.Input.View()
}

// Value returns the current input text.
func (m Model) Value() string {
	return m.Input.Value()
}

// SetValue sets the input text.
func (m Model) SetValue(v string) {
	m.Input.SetValue(v)
}

// Focused returns whether the input is focused.
func (m Model) Focused() bool {
	return m.Input.Focused()
}

// Focus sets focus on the input.
func (m Model) Focus() tea.Cmd {
	return m.Input.Focus()
}

// Blur removes focus from the input.
func (m Model) Blur() {
	m.Input.Blur()
}

// IsSlashCommand checks if the text is a slash command.
func (m Model) IsSlashCommand(text string) bool {
	if !strings.HasPrefix(text, "/") {
		return false
	}
	cmd, _, _ := strings.Cut(text, " ")
	_, ok := m.Commands[cmd]
	return ok
}

// ParseCommand splits text into command and args.
func (m Model) ParseCommand(text string) (cmd, args string) {
	if !strings.HasPrefix(text, "/") {
		return "", text
	}
	parts := strings.SplitN(text, " ", 2)
	cmd = parts[0]
	if len(parts) > 1 {
		args = parts[1]
	}
	return cmd, args
}

// cycleAutocomplete cycles through matching commands.
func (m *Model) cycleAutocomplete() {
	val := m.Input.Value()
	if !strings.HasPrefix(val, "/") {
		return
	}

	for _, ac := range m.Autocomplete {
		if strings.HasPrefix(ac, val) && ac != val {
			m.Input.SetValue(ac + " ")
			return
		}
	}
}

// HelpView returns the help screen as a string.
func (m Model) HelpView() string {
	var b strings.Builder
	b.WriteString(theme.HelpTitle.Render("Commands"))
	b.WriteString("\n\n")

	for cmd, info := range m.Commands {
		b.WriteString(theme.HelpKey.Render(cmd))
		b.WriteString("  ")
		b.WriteString(theme.HelpDesc.Render(info.Desc))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(theme.HelpDesc.Render("Tab: autocomplete  •  Enter: submit  •  Esc: cancel/focus"))
	return b.String()
}