// Package types defines shared types for the aiw-tui IPC protocol.
package types

import "encoding/json"

// Command sent from TUI → backend over stdin.
type Command struct {
	Cmd       string `json:"cmd"`
	Task      string `json:"task,omitempty"`
	Model     string `json:"model,omitempty"`
	Query     string `json:"query,omitempty"` // kb_search
	SessionID string `json:"session_id,omitempty"`
	Section   string `json:"section,omitempty"` // dashboard
	Action    string `json:"action,omitempty"`  // sessions, context
	Provider  string `json:"provider,omitempty"`
	Path      string `json:"path,omitempty"`     // filebrowser
	Messages  []any  `json:"messages,omitempty"` // chat history
}

// Event received from backend → TUI over stdout (NDJSON).
type Event struct {
	Type string          `json:"type"`
	Data json.RawMessage `json:"data"`
}

// Event payload types (data field parsed by event type).

type TokenData struct {
	Text string `json:"text"`
}

type ThinkingData struct {
	Text string `json:"text"`
}

type ToolCallData struct {
	Name string         `json:"name"`
	Args map[string]any `json:"args"`
	ID   string         `json:"id"`
}

type ToolResultData struct {
	ID       string  `json:"id"`
	Result   string  `json:"result"`
	Duration float64 `json:"duration"`
}

type DoneData struct {
	Reason string  `json:"reason"`
	Tokens int     `json:"tokens"`
	Cost   float64 `json:"cost"`
}

type ErrorData struct {
	Message string `json:"message"`
}

type PhaseData struct {
	Phase string `json:"phase"`
}

type StatusData struct {
	Running bool    `json:"running"`
	Tokens  int     `json:"tokens"`
	Cost    float64 `json:"cost"`
	Model   string  `json:"model"`
}

type ResultData struct {
	// Generic result — fields depend on command
	Raw map[string]any `json:"-"`
}

// Chat message types for the TUI display.
type MessageType int

const (
	MsgUser MessageType = iota
	MsgAssistant
	MsgThinking
	MsgToolCall
	MsgToolResult
	MsgError
	MsgSystem
)

type Message struct {
	Type     MessageType
	Content  string
	Step     int
	ToolID   string
	ToolName string
	ToolArgs map[string]any
}

// Session summary for session list.
type SessionSummary struct {
	ID         string `json:"id"`
	Model      string `json:"model"`
	Summary    string `json:"summary"`
	CreatedAt  string `json:"created_at"`
	EntryCount int    `json:"entry_count"`
}

// Dashboard data.
type DashboardData struct {
	Stats    map[string]any `json:"stats"`
	Health   map[string]any `json:"health"`
	Activity []string       `json:"activity"`
	Cost     map[string]any `json:"cost"`
}

// Context file entry.
type ContextFile struct {
	Path   string `json:"path"`
	Tokens int    `json:"tokens"`
	Status string `json:"status"`
	Lines  int    `json:"lines"`
}

// Context data.
type ContextData struct {
	Files        []ContextFile `json:"files"`
	TotalTokens  int           `json:"total_tokens"`
}

// Git status data.
type GitData struct {
	Branch string      `json:"branch"`
	Status []GitEntry  `json:"status"`
	Log    []GitCommit `json:"log"`
}

type GitEntry struct {
	Flag string `json:"flag"`
	Path string `json:"path"`
}

type GitCommit struct {
	Hash    string `json:"hash"`
	Message string `json:"message"`
}

// FileBrowser entry.
type FileEntry struct {
	Name     string  `json:"name"`
	Path     string  `json:"path"`
	IsDir    bool    `json:"is_dir"`
	Size     int64   `json:"size"`
	Modified float64 `json:"modified"`
}

type FileBrowserData struct {
	Entries []FileEntry `json:"entries"`
	Current string      `json:"current"`
	Parent  string      `json:"parent"`
	Error   string      `json:"error,omitempty"`
}