// aiw-tui — Go Bubble Tea TUI client for AI Workspace.
//
// Spawns the Python backend (aiw tui-server --stdio) and communicates
// over stdin/stdout using NDJSON (Newline-Delimited JSON).
package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"os"

	tea "github.com/charmbracelet/bubbletea"

	"aiw-tui/app"
	"aiw-tui/ipc"
	"aiw-tui/types"
)

const version = "0.1.0"

func main() {
	backendCmd := flag.String("backend", "", "Backend command (default: aiw tui-server --stdio)")
	showVersion := flag.Bool("version", false, "Show version and exit")
	debug := flag.Bool("debug", false, "Enable debug logging")
	flag.Parse()

	if *showVersion {
		fmt.Printf("aiw-tui v%s\n", version)
		fmt.Println("Go Bubble Tea TUI client for AI Workspace")
		os.Exit(0)
	}

	if *debug {
		log.SetFlags(log.Ltime | log.Lshortfile)
	} else {
		log.SetOutput(io.Discard)
	}

	// Use custom backend command or default
	cmdParts := []string{"aiw", "tui-server", "--stdio"}
	if *backendCmd != "" {
		cmdParts = []string{*backendCmd}
	}

	// Check if we have a real TTY before attempting TUI
	if !isTerminal() {
		fmt.Fprintln(os.Stderr, "Error: aiw-tui requires a real terminal (TTY).")
		fmt.Fprintln(os.Stderr, "Run 'aiw-tui --help' for usage.")
		fmt.Fprintf(os.Stderr, "If you want to test the backend, run:\n  echo '{\"cmd\":\"models\"}' | aiw tui-server --stdio\n")
		os.Exit(1)
	}

	// Spawn the Python backend process
	client, err := ipc.NewClient(cmdParts...)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to start backend: %v\n", err)
		fmt.Fprintln(os.Stderr, "")
		fmt.Fprintln(os.Stderr, "Make sure 'aiw' is installed and in PATH.")
		fmt.Fprintln(os.Stderr, "  nix run .#aiw -- --help    # test Python CLI")
		fmt.Fprintln(os.Stderr, "  which aiw                   # check PATH")
		os.Exit(1)
	}
	defer client.Close()

	// Verify backend is alive
	if err := pingBackend(client); err != nil {
		fmt.Fprintf(os.Stderr, "Error: backend not responding: %v\n", err)
		os.Exit(1)
	}

	// Create and run the Bubble Tea program
	m := app.New(client, 80, 24)
	p := tea.NewProgram(
		m,
		tea.WithAltScreen(),
		tea.WithMouseCellMotion(),
	)

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "\nError: TUI crashed: %v\n", err)
		fmt.Fprintln(os.Stderr, "")
		fmt.Fprintln(os.Stderr, "Try running with --debug for more details:")
		fmt.Fprintln(os.Stderr, "  aiw-tui --debug")
		os.Exit(1)
	}
}

// isTerminal checks if we're running in a real terminal.
func isTerminal() bool {
	// Try to open /dev/tty — if it fails, there's no real terminal
	f, err := os.OpenFile("/dev/tty", os.O_RDWR, 0)
	if err != nil {
		return false
	}
	f.Close()
	return true
}

// pingBackend verifies the backend is alive by sending a models command.
func pingBackend(client *ipc.Client) error {
	if err := client.Send(types.Command{Cmd: "models"}); err != nil {
		return fmt.Errorf("send ping: %w", err)
	}
	event, err := client.ReadEvent()
	if err != nil {
		return fmt.Errorf("read ping response: %w", err)
	}
	if event == nil || event.Type == "error" {
		return errors.New("backend returned error on ping")
	}
	return nil
}