// Package statusbar implements the bottom status bar for aiw-tui.
package statusbar

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"aiw-tui/theme"
)

// State represents the current status bar state.
type State struct {
	Model     string
	Tokens    int
	Cost      float64
	Running   bool
	SessionID string
}

// Model is the status bar component.
type Model struct {
	State State
	Width int
}

// New creates a new status bar model.
func New() Model {
	return Model{
		State: State{
			Model: "qwen3:14b",
		},
	}
}

// Update updates the status bar state.
func (m *Model) Update(state State) {
	m.State = state
}

// View renders the status bar.
func (m Model) View() string {
	if m.Width == 0 {
		return ""
	}

	var sections []string

	// Model indicator
	modelSection := theme.StatusBarStyle.Render(fmt.Sprintf(" %s ", m.State.Model))
	sections = append(sections, modelSection)

	// Agent status
	statusText := "● Idle"
	statusColor := theme.Faint
	if m.State.Running {
		statusText = "● Running"
		statusColor = theme.Success
	}
	statusStyle := theme.StatusBarStyle.Copy().Foreground(statusColor)
	sections = append(sections, statusStyle.Render(statusText))

	// Token count
	if m.State.Tokens > 0 {
		tokenStr := fmt.Sprintf(" %d tokens ", m.State.Tokens)
		sections = append(sections, theme.StatusBarDim.Render(tokenStr))
	}

	// Cost
	if m.State.Cost > 0 {
		costStr := fmt.Sprintf(" $%.2f ", m.State.Cost)
		sections = append(sections, theme.StatusBarDim.Render(costStr))
	}

	// Session (right-aligned)
	sessionStr := fmt.Sprintf(" session: %s ", m.State.SessionID)

	// Build the full bar
	leftContent := lipgloss.JoinHorizontal(lipgloss.Top, sections...)
	leftWidth := lipgloss.Width(leftContent)

	rightContent := theme.StatusBarDim.Render(sessionStr)
	rightWidth := lipgloss.Width(rightContent)

	padding := m.Width - leftWidth - rightWidth
	if padding < 1 {
		padding = 1
	}

	bar := lipgloss.JoinHorizontal(
		lipgloss.Top,
		leftContent,
		strings.Repeat(" ", padding),
		rightContent,
	)

	return theme.StatusBarStyle.Render(bar)
}