// Package theme defines the visual theme for aiw-tui.
package theme

import "github.com/charmbracelet/lipgloss"

// Colors — same palette as the Textual v5 workstation theme.
var (
	Primary   = lipgloss.Color("#5B8DEE")
	Secondary = lipgloss.Color("#7C8DB5")
	Accent    = lipgloss.Color("#5B8DEE")
	Warning   = lipgloss.Color("#D4A853")
	Error     = lipgloss.Color("#E0556A")
	Success   = lipgloss.Color("#5FA874")
	BG        = lipgloss.Color("#0F1117")
	Surface   = lipgloss.Color("#1D1F2B")
	Panel     = lipgloss.Color("#1D1F2B")
	Text      = lipgloss.Color("#A0A5B8")
	Faint     = lipgloss.Color("#6E7082")
	TextDim   = lipgloss.Color("#7C8DB5")
)

// Pre-built styles for common UI elements.
var (
	// App styles
	AppStyle = lipgloss.NewStyle().
			Background(BG)

	// Chat styles
	UserMsgStyle = lipgloss.NewStyle().
			Foreground(Primary).
			Bold(true).
			Padding(0, 2)
	AssistantMsgStyle = lipgloss.NewStyle().
				Foreground(Text).
				Padding(0, 2)
	ThinkingStyle = lipgloss.NewStyle().
			Foreground(Faint).
			Italic(true).
			Padding(0, 2)
	ErrorStyle = lipgloss.NewStyle().
			Foreground(Error).
			Padding(0, 2)
	SystemStyle = lipgloss.NewStyle().
			Foreground(Secondary).
			Italic(true).
			Padding(0, 2)

	// Tool call styles
	ToolCallHeader = lipgloss.NewStyle().
			Foreground(Warning).
			Bold(true)
	ToolResultBody = lipgloss.NewStyle().
			Foreground(Faint)

	// Input styles
	InputStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(Primary).
			Padding(0, 1)

	// Status bar styles
	StatusBarStyle = lipgloss.NewStyle().
			Background(Surface).
			Foreground(Text).
			Padding(0, 1)
	StatusBarDim = lipgloss.NewStyle().
			Background(Surface).
			Foreground(Faint)

	// Dashboard styles
	DashboardTitle = lipgloss.NewStyle().
			Foreground(Primary).
			Bold(true).
			Padding(0, 1)
	StatLabel = lipgloss.NewStyle().
			Foreground(Faint).
			Width(12)
	StatValue = lipgloss.NewStyle().
			Foreground(Text).
			Bold(true)

	// Context inspector styles
	ContextPath = lipgloss.NewStyle().
			Foreground(Text).
			Width(40)
	ContextTokens = lipgloss.NewStyle().
			Foreground(Warning).
			Width(8).
			Align(lipgloss.Right)
	ContextStatus = lipgloss.NewStyle().
			Width(10)

	// Git panel styles
	GitBranch = lipgloss.NewStyle().
			Foreground(Success).
			Bold(true)
	GitChanged = lipgloss.NewStyle().
			Foreground(Warning)
	GitAdded = lipgloss.NewStyle().
			Foreground(Success)
	GitUntracked = lipgloss.NewStyle().
			Foreground(Faint)

	// File browser styles
	DirStyle = lipgloss.NewStyle().
			Foreground(Primary).
			Bold(true)
	FileStyle = lipgloss.NewStyle().
			Foreground(Text)
	ParentStyle = lipgloss.NewStyle().
			Foreground(Faint).
			Italic(true)

	// Help screen
	HelpKey = lipgloss.NewStyle().
			Foreground(Primary).
			Bold(true)
	HelpDesc = lipgloss.NewStyle().
			Foreground(Text)
	HelpTitle = lipgloss.NewStyle().
			Foreground(Accent).
			Bold(true).
			Padding(0, 1)
)