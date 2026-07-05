package ipc

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"sync"

	"aiw-tui/types"
)

// Client manages the stdio IPC connection to the Python backend.
//
// Usage:
//
//	client, err := ipc.NewClient("aiw", "tui-server", "--stdio")
//	defer client.Close()
//	client.Send(types.Command{Cmd: "models", Provider: "ollama"})
//	event, err := client.ReadEvent()
type Client struct {
	stdin  io.WriteCloser
	stdout io.ReadCloser
	reader *bufio.Scanner
	cmd    *exec.Cmd
	mu     sync.Mutex
}

// NewClient spawns the backend process and opens the IPC pipes.
func NewClient(backendCmd ...string) (*Client, error) {
	if len(backendCmd) == 0 {
		backendCmd = []string{"aiw", "tui-server", "--stdio"}
	}

	cmd := exec.Command(backendCmd[0], backendCmd[1:]...)

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("stdin pipe: %w", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("stdout pipe: %w", err)
	}

	// Stderr is inherited from the parent process for debugging
	cmd.Stderr = nil

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("spawn backend: %w", err)
	}

	return &Client{
		stdin:  stdin,
		stdout: stdout,
		reader: bufio.NewScanner(stdout),
		cmd:    cmd,
	}, nil
}

// Send marshals a Command and writes it as a JSON line to stdin.
func (c *Client) Send(cmd types.Command) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	data, err := json.Marshal(cmd)
	if err != nil {
		return fmt.Errorf("marshal command: %w", err)
	}

	data = append(data, '\n')
	if _, err := c.stdin.Write(data); err != nil {
		return fmt.Errorf("write command: %w", err)
	}

	return nil
}

// ReadEvent reads the next NDJSON line from stdout and parses it as an Event.
func (c *Client) ReadEvent() (*types.Event, error) {
	if !c.reader.Scan() {
		if err := c.reader.Err(); err != nil {
			return nil, fmt.Errorf("read event: %w", err)
		}
		return nil, io.EOF
	}

	line := c.reader.Text()
	if line == "" {
		return nil, fmt.Errorf("empty event line")
	}

	var event types.Event
	if err := json.Unmarshal([]byte(line), &event); err != nil {
		return nil, fmt.Errorf("parse event: %w (line: %s)", err, line[:min(len(line), 100)])
	}

	return &event, nil
}

// Close sends the quit command and waits for the backend to exit.
func (c *Client) Close() error {
	// Send quit command
	_ = c.Send(types.Command{Cmd: "quit"})

	// Close stdin to signal EOF
	c.stdin.Close()

	// Wait for process to exit
	return c.cmd.Wait()
}

// Kill forces the backend process to terminate.
func (c *Client) Kill() {
	if c.cmd != nil && c.cmd.Process != nil {
		c.cmd.Process.Kill()
	}
}

// Pid returns the process ID of the backend.
func (c *Client) Pid() int {
	if c.cmd != nil && c.cmd.Process != nil {
		return c.cmd.Process.Pid
	}
	return 0
}

// EventReader is an interface for components that consume events.
type EventReader interface {
	HandleEvent(event *types.Event) error
}