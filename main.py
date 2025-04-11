import os
import sys
import json
import datetime
import uuid
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class GitCommit:
    def __init__(self, commit_id, message, parent=None, second_parent=None):
        self.id = commit_id
        self.message = message
        self.parent = parent
        self.second_parent = second_parent
        self.timestamp = datetime.datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'parent': self.parent,
            'second_parent': self.second_parent,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        commit = cls(data['id'], data['message'], data['parent'], data.get('second_parent'))
        commit.timestamp = datetime.datetime.fromisoformat(data['timestamp'])
        return commit

class GitBranch:
    def __init__(self, name, head, color=None):
        self.name = name
        self.head = head
        self.color = color or self._generate_color()
    
    def _generate_color(self):
        colors = ['#2196f3', '#4caf50', '#9c27b0', '#ff9800', '#e91e63', '#607d8b']
        import random
        return random.choice(colors)
    
    def to_dict(self):
        return {
            'name': self.name,
            'head': self.head,
            'color': self.color
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['name'], data['head'], data['color'])

class GitRepository:
    def __init__(self):
        self.commits = {}
        self.branches = {}
        self.current_branch = None
        
        # Initialize with a first commit and master branch
        self._initialize_repo()
    
    def _initialize_repo(self):
        # Create initial commit
        initial_commit = GitCommit('C0', 'Initial commit')
        self.commits[initial_commit.id] = initial_commit
        
        # Create master branch pointing to initial commit
        master_branch = GitBranch('master', initial_commit.id)
        self.branches[master_branch.name] = master_branch
        
        # Set current branch to master
        self.current_branch = 'master'
    
    def create_commit(self, message):
        # Get current branch
        branch = self.branches.get(self.current_branch)
        if not branch:
            return False, f"Error: Current branch '{self.current_branch}' not found"
        
        # Get parent commit ID
        parent_id = branch.head
        
        # Create new commit
        commit_id = f"C{len(self.commits)}"
        new_commit = GitCommit(commit_id, message, parent_id)
        self.commits[commit_id] = new_commit
        
        # Update branch head
        branch.head = commit_id
        
        return True, f"Created commit {commit_id}: {message}"
    
    def create_branch(self, name):
        if name in self.branches:
            return False, f"Error: Branch '{name}' already exists"
        
        current_head = self.branches[self.current_branch].head
        new_branch = GitBranch(name, current_head)
        self.branches[name] = new_branch
        
        return True, f"Created branch '{name}' at commit {current_head}"
    
    def checkout_branch(self, name):
        if name not in self.branches:
            return False, f"Error: Branch '{name}' not found"
        
        self.current_branch = name
        
        return True, f"Switched to branch '{name}'"
    
    def merge_branches(self, source_branch_name):
        # Get target and source branches
        target_branch = self.branches.get(self.current_branch)
        source_branch = self.branches.get(source_branch_name)
        
        if not source_branch:
            return False, f"Error: Branch '{source_branch_name}' not found"
        
        # Check if merge is needed
        if target_branch.head == source_branch.head:
            return True, "Already up to date. Nothing to merge."
        
        # Create merge commit
        commit_id = f"C{len(self.commits)}"
        message = f"Merge branch '{source_branch_name}' into {self.current_branch}"
        merge_commit = GitCommit(commit_id, message, target_branch.head, source_branch.head)
        self.commits[commit_id] = merge_commit
        
        # Update branch head
        target_branch.head = commit_id
        
        return True, f"Merged '{source_branch_name}' into '{self.current_branch}'"
    
    def get_commit_log(self):
        branch = self.branches.get(self.current_branch)
        if not branch:
            return "Error: Current branch not found"
        
        result = []
        current_commit_id = branch.head
        
        while current_commit_id:
            commit = self.commits.get(current_commit_id)
            if not commit:
                break
            
            result.append(f"Commit: {commit.id}")
            result.append(f"Message: {commit.message}")
            result.append(f"Date: {commit.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            result.append("")
            
            current_commit_id = commit.parent
        
        return "\n".join(result) if result else "No commits yet"
    
    def save_to_file(self, filename):
        data = {
            'commits': {commit_id: commit.to_dict() for commit_id, commit in self.commits.items()},
            'branches': {branch_name: branch.to_dict() for branch_name, branch in self.branches.items()},
            'current_branch': self.current_branch,
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        
        repo = cls()
        repo.commits = {}
        repo.branches = {}
        
        for commit_id, commit_data in data['commits'].items():
            repo.commits[commit_id] = GitCommit.from_dict(commit_data)
        
        for branch_name, branch_data in data['branches'].items():
            repo.branches[branch_name] = GitBranch.from_dict(branch_data)
        
        repo.current_branch = data['current_branch']
        repo.head = data['head']
        
        return repo
    
    def build_graph(self):
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add nodes (commits)
        for commit_id, commit in self.commits.items():
            G.add_node(commit_id, label=commit_id)
            
            # Add edges (parent relationships)
            if commit.parent:
                G.add_edge(commit.parent, commit_id)
            if commit.second_parent:
                G.add_edge(commit.second_parent, commit_id)
        
        return G

class GitSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Git Branching Simulator")
        self.root.geometry("1000x600")
        
        self.repo = GitRepository()
        
        self._create_ui()
        self._update_graph()
    
    def _create_ui(self):
        self.root.columnconfigure(0, weight=2)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Left panel (Graph visualization)
        left_panel = ttk.Frame(self.root)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, left_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Right panel (Terminal)
        right_panel = ttk.Frame(self.root)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=0)
        
        # Terminal output
        self.terminal_output = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD, bg='black', fg='white')
        self.terminal_output.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.terminal_output.insert(tk.END, "Git Branching Simulator\n")
        self.terminal_output.insert(tk.END, "Type 'help' for available commands\n")
        self.terminal_output.insert(tk.END, "\n")
        
        # Command input frame
        cmd_frame = ttk.Frame(right_panel)
        cmd_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        cmd_frame.columnconfigure(1, weight=1)
        
        ttk.Label(cmd_frame, text="$").grid(row=0, column=0, padx=5)
        
        self.cmd_entry = ttk.Entry(cmd_frame)
        self.cmd_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.cmd_entry.bind("<Return>", self._execute_command)
        
        execute_btn = ttk.Button(cmd_frame, text="Execute", command=self._execute_command)
        execute_btn.grid(row=0, column=2, padx=5)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        
        self.status_label = ttk.Label(status_frame, text=f"Current branch: {self.repo.current_branch}")
        self.status_label.pack(side=tk.LEFT)
        
    def _execute_command(self, event=None):
        command = self.cmd_entry.get().strip()
        if not command:
            return
        
        self.terminal_output.insert(tk.END, f"$ {command}\n")
        self.cmd_entry.delete(0, tk.END)
        
        args = command.split()
        cmd = args[0].lower()
        
        result = self._process_command(cmd, args[1:])
        self.terminal_output.insert(tk.END, f"{result}\n\n")
        self.terminal_output.see(tk.END)
        
        # Update graph and status
        self._update_graph()
        self._update_status()
    
    def _process_command(self, cmd, args):
        if cmd == "help":
            return self._show_help()
        elif cmd == "commit":
            message = " ".join(args) if args else "New commit"
            success, result = self.repo.create_commit(message)
            return result
        elif cmd == "branch":
            if not args:
                return "Error: Branch name required"
            return self.repo.create_branch(args[0])[1]
        elif cmd == "checkout":
            if not args:
                return "Error: Branch name required"
            return self.repo.checkout_branch(args[0])[1]
        elif cmd == "merge":
            if not args:
                return "Error: Source branch required"
            return self.repo.merge_branches(args[0])[1]
        elif cmd == "log":
            return self.repo.get_commit_log()
        elif cmd == "clear":
            self.terminal_output.delete(1.0, tk.END)
            return ""
        elif cmd == "save":
            filename = args[0] if args else "git_repo.json"
            self.repo.save_to_file(filename)
            return f"Repository saved to {filename}"
        elif cmd == "load":
            if not args:
                return "Error: Filename required"
            filename = args[0]
            if not os.path.exists(filename):
                return f"Error: File {filename} not found"
            try:
                self.repo = GitRepository.load_from_file(filename)
                return f"Repository loaded from {filename}"
            except Exception as e:
                return f"Error loading repository: {str(e)}"
        else:
            return f"Unknown command: {cmd}. Type 'help' for available commands."
    
    def _show_help(self):
        return """Available commands:
- commit [message]: Create a new commit
- branch <name>: Create a new branch
- checkout <name>: Switch to another branch
- merge <branch>: Merge another branch into current
- log: Show commit history
- clear: Clear terminal output
- save [filename]: Save repository to file
- load <filename>: Load repository from file
- help: Show this help message"""
    
    def _update_status(self):
        self.status_label.config(text=f"Current branch: {self.repo.current_branch}")
    
    def _update_graph(self):
        self.ax.clear()
        
        # Get graph from repository
        G = self.repo.build_graph()
        
        # Use hierarchical layout
        pos = nx.spring_layout(G, seed=42)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=700, ax=self.ax)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, ax=self.ax)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, ax=self.ax)
        
        # Draw branch labels
        for branch_name, branch in self.repo.branches.items():
            commit_id = branch.head
            if commit_id in pos:
                x, y = pos[commit_id]
                color = branch.color
                is_current = branch_name == self.repo.current_branch
                self.ax.text(x, y + 0.1, branch_name, 
                           bbox=dict(facecolor=color, alpha=0.7, edgecolor='black' if is_current else 'none', boxstyle='round,pad=0.5'),
                           ha='center', color='white', fontweight='bold')
        
        self.ax.set_title("Git Repository Visualization")
        self.ax.axis('off')
        
        # Update canvas
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = GitSimulatorApp(root)
    root.mainloop()