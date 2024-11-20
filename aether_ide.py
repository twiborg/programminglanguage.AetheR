import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from interpreter import Interpreter

class ModernTheme:
    BG_DARK = "#141414"
    BG_DARKER = "#1e1e1e"
    BG_LIGHTER = "#252525"
    FG_NORMAL = "#ffffff"
    FG_DIMMED = "#858585"
    ACCENT = "#569cd6"
    SELECTION = "#264f78"
    CURRENT_LINE = "#1e1e1e"
    ERROR_COLOR = "#ff0000"
    SCROLLBAR_BG = "#1e1e1e"
    SCROLLBAR_FG = "#424242"
    
    KEYWORD_COLOR = "#569cd6"
    STRING_COLOR = "#ce9178"
    ESCAPE_COLOR = "#d7ba7d"
    NUMBER_COLOR = "#b5cea8"
    OPERATOR_COLOR = "#d4d4d4"
    COMMENT_COLOR = "#6a9955"
    IDENTIFIER_COLOR = "#9cdcfe"
    LOOP_COLOR = "#C586C0"
    FUNCTION_COLOR = "#dcdcaa"
    CODE_FONT = ('Consolas', 12)
    UI_FONT = ("Segoe UI", 10)

class LineNumbers(tk.Canvas):
    def __init__(self, parent, text_widget, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.text_widget = text_widget
        self.config(width=45, bg=ModernTheme.BG_DARKER, highlightthickness=0)
        
        self.text_widget.bind('<<Modified>>', self._on_change)
        self.text_widget.bind('<Configure>', self._on_change)
        self.text_widget.bind('<MouseWheel>', self._on_change)
        self.text_widget.bind('<KeyPress>', self._on_change)
        
        self._redraw()
    
    def _on_change(self, event=None):
        self.text_widget.edit_modified(False)
        self._redraw()
    
    def _redraw(self, event=None):
        self.delete('all')
        
        first_index = self.text_widget.index("@0,0")
        last_index = self.text_widget.index(f"@0,{self.text_widget.winfo_height()}")
        
        first_line = int(float(first_index))
        last_line = int(float(last_index)) + 1
        
        for line_num in range(first_line, last_line):
            dline = self.text_widget.dlineinfo(f"{line_num}.0")
            if dline:
                y = dline[1] + dline[3] // 2  
                self.create_text(
                    40, y,
                    anchor='e',
                    text=str(line_num),
                    fill=ModernTheme.FG_DIMMED,
                    font=ModernTheme.CODE_FONT
                )

class ModernScrollbar(ttk.Scrollbar):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        style = ttk.Style()
        style.layout('Modern.Vertical.TScrollbar', 
                    [('Vertical.Scrollbar.trough',
                      {'children': [('Vertical.Scrollbar.thumb', {'expand': '1'})],
                       'sticky': 'ns'})])
        
        style.layout('Modern.Horizontal.TScrollbar', 
                    [('Horizontal.Scrollbar.trough',
                      {'children': [('Horizontal.Scrollbar.thumb', {'expand': '1'})],
                       'sticky': 'we'})])
        
        style.configure('Modern.Vertical.TScrollbar',
                       background=ModernTheme.SCROLLBAR_FG,
                       troughcolor=ModernTheme.SCROLLBAR_BG,
                       width=10,
                       arrowsize=0)
        
        style.configure('Modern.Horizontal.TScrollbar',
                       background=ModernTheme.SCROLLBAR_FG,
                       troughcolor=ModernTheme.SCROLLBAR_BG,
                       width=10,
                       arrowsize=0)
        
        if kwargs.get('orient') == 'vertical':
            self.configure(style='Modern.Vertical.TScrollbar')
        else:
            self.configure(style='Modern.Horizontal.TScrollbar')

class StatusBar(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config(style='Status.TFrame')
        
        self.status_label = ttk.Label(
            self, 
            text="Ready", 
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.position_label = ttk.Label(
            self, 
            text="Ln 1, Col 1", 
            style='Status.TLabel'
        )
        self.position_label.pack(side=tk.RIGHT, padx=5)
    
    def set_status(self, text):
        self.status_label.config(text=text)
    
    def update_position(self, line, col):
        self.position_label.config(text=f"Ln {line}, Col {col}")

class ModernEditor(tk.Text):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        keywords = r'(?:var|print|true|false|nil|if|else|return|while|for|fun|length|find|replace)'
        
        self.syntax_patterns = {
            'keyword': re.compile(fr'\b{keywords}\b'),
            'loop': re.compile(r'\b(?:while|for)\b'),
            'function': re.compile(r'\b(?:fun)\b'),
            'function_call': re.compile(fr'\b(?!{keywords}\b)[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\()'),
            'string': re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'),
            'escape': re.compile(r'\\[ntr"\\]'),
            'number': re.compile(r'\b\d+(?:\.\d+)?\b'),
            'operator': re.compile(r'[+\-*/=]|==|!=|>=|<=|>|<'),
            'comment': re.compile(r'//.*$', re.MULTILINE)
        }
        
        self.config(
            wrap=tk.NONE,
            undo=True,
            bg=ModernTheme.BG_DARK,
            fg=ModernTheme.FG_NORMAL,
            insertbackground=ModernTheme.FG_NORMAL,
            selectbackground=ModernTheme.SELECTION,
            selectforeground=ModernTheme.FG_NORMAL,
            font=ModernTheme.CODE_FONT,
            relief=tk.FLAT,
            padx=5,
            pady=5,
            inactiveselectbackground=ModernTheme.SELECTION
        )

        self.bind('<Control-a>', self._select_all)
        self.bind('<Control-c>', self._copy)
        self.bind('<Control-x>', self._cut)
        self.bind('<Control-v>', self._paste)
        self.bind('<Control-z>', self._undo)
        self.bind('<Control-y>', self._redo)
        self.bind('<Control-s>', self._save)
        
        self.bind('<Tab>', self._handle_tab)
        
        self.bind('(', lambda e: self._auto_pair(e, '(', ')'))
        self.bind('{', lambda e: self._auto_pair(e, '{', '}'))
        self.bind('[', lambda e: self._auto_pair(e, '[', ']'))
        self.bind('"', lambda e: self._auto_pair(e, '"', '"'))
        
        self.tag_configure('current_line', background=ModernTheme.CURRENT_LINE)
        self.tag_configure('error_line', background='#660000')
        self.tag_configure('keyword', foreground=ModernTheme.KEYWORD_COLOR)
        self.tag_configure('loop', foreground=ModernTheme.LOOP_COLOR)
        self.tag_configure('function', foreground=ModernTheme.FUNCTION_COLOR)
        self.tag_configure('function_call', foreground=ModernTheme.FUNCTION_COLOR)
        self.tag_configure('string', foreground=ModernTheme.STRING_COLOR)
        self.tag_configure('escape', foreground=ModernTheme.ESCAPE_COLOR)
        self.tag_configure('number', foreground=ModernTheme.NUMBER_COLOR)
        self.tag_configure('operator', foreground=ModernTheme.OPERATOR_COLOR)
        self.tag_configure('comment', foreground=ModernTheme.COMMENT_COLOR)
        self.tag_configure('identifier', foreground=ModernTheme.IDENTIFIER_COLOR)

        self.tag_raise('error_line')
        self.tag_lower('current_line')
        
        self.bind('<KeyRelease>', self._on_key_release)
        self.bind('<Button-1>', self._on_key_release)
        
        self._highlight_timer = None
        self._error_line = None  

    def highlight_error(self, line_number):
        print(f"DEBUG: Highlighting error line {line_number}")
        
        self.clear_error_highlight()
        
        if line_number is not None:
            start = f"{line_number}.0"
            end = f"{line_number}.end"
            
            print(f"DEBUG: Adding tag from {start} to {end}")
            self.tag_add('error_line', start, end)
            
            self.see(start)
            print("DEBUG: Tag added and scrolled to line")
            
            self.update_idletasks()
            print("DEBUG: UI updated")
            
            self._error_line = line_number

    def clear_error_highlight(self):
        print("DEBUG: Clearing error highlight")
        if self._error_line is not None:
            start = f"{self._error_line}.0"
            end = f"{self._error_line}.end"
            print(f"DEBUG: Removing tag from {start} to {end}")
            self.tag_remove('error_line', start, end)
            self._error_line = None
            print("DEBUG: Tag removed")
    
    def _on_key_release(self, event=None):
        if self._highlight_timer is not None:
            self.after_cancel(self._highlight_timer)
        
        self._highlight_timer = self.after(10, self._delayed_highlight)
        
    def _delayed_highlight(self):
        self._highlight_current_line()
        self._highlight_all_syntax()
        
    def _highlight_current_line(self):
        self.tag_remove('current_line', '1.0', tk.END)
        current_line = self.index(tk.INSERT).split('.')[0]
        self.tag_add('current_line', f'{current_line}.0', f'{current_line}.end+1c')
        
    def _highlight_all_syntax(self):
        content = self.get('1.0', tk.END)
        
        # Сохраняем текущее выделение
        try:
            sel_start = self.index(tk.SEL_FIRST)
            sel_end = self.index(tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False
        
        # Удаляем все теги кроме current_line, error_line и sel
        for tag in self.tag_names():
            if tag not in ['current_line', 'error_line', 'sel']:
                self.tag_remove(tag, '1.0', tk.END)
        
        # Сначала подсвечиваем комментарии
        for match in self.syntax_patterns['comment'].finditer(content):
            start = match.start()
            end = match.end()
            start_index = f"1.0+{start}c"
            end_index = f"1.0+{end}c"
            self.tag_add('comment', start_index, end_index)

        # Затем строки и escape-последовательности внутри них
        for match in self.syntax_patterns['string'].finditer(content):
            start = match.start()
            end = match.end()
            start_index = f"1.0+{start}c"
            end_index = f"1.0+{end}c"
            
            # Сначала подсвечиваем всю строку
            self.tag_add('string', start_index, end_index)
            
            # Затем внутри строки ищем и подсвечиваем escape-последовательности
            string_content = match.group()
            escape_pattern = self.syntax_patterns['escape']
            for escape_match in escape_pattern.finditer(string_content):
                escape_start = start + escape_match.start()
                escape_end = start + escape_match.end()
                escape_start_index = f"1.0+{escape_start}c"
                escape_end_index = f"1.0+{escape_end}c"
                self.tag_add('escape', escape_start_index, escape_end_index)

        # Затем все остальные элементы, но только если они не внутри строк или комментариев
        for pattern_name, pattern in self.syntax_patterns.items():
            if pattern_name not in ['string', 'escape', 'comment']:
                for match in pattern.finditer(content):
                    start = match.start()
                    end = match.end()
                    start_index = f"1.0+{start}c"
                    end_index = f"1.0+{end}c"
                    
                    # Проверяем, не находится ли совпадение внутри строки или комментария
                    if not (self.tag_nextrange('string', start_index, end_index) or 
                           self.tag_nextrange('comment', start_index, end_index)):
                        self.tag_add(pattern_name, start_index, end_index)
        
        # Восстанавливаем выделение
        if has_selection:
            self.tag_add('sel', sel_start, sel_end)

    def _select_all(self, event=None):
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, tk.END)
        return "break"

    def _copy(self, event=None):
        try:
            selection = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selection)
        except tk.TclError:
            pass
        return "break"

    def _cut(self, event=None):
        try:
            selection = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selection)
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        return "break"

    def _paste(self, event=None):
        try:
            self.insert(tk.INSERT, self.clipboard_get())
        except tk.TclError:
            pass
        return "break"

    def _undo(self, event=None):
        try:
            self.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _redo(self, event=None):
        try:
            self.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def _save(self, event=None):
        return "break"

    def _handle_tab(self, event=None):
        self.insert(tk.INSERT, " " * 4)
        return "break"

    def _auto_pair(self, event, opening, closing):
        self.insert(tk.INSERT, opening + closing)
        self.mark_set(tk.INSERT, f"{tk.INSERT}-1c")
        return "break"

class Console(tk.Text):
    def __init__(self, parent, *args, **kwargs):
        kwargs.update({
            'wrap': tk.WORD,
            'background': ModernTheme.BG_DARKER,
            'foreground': ModernTheme.FG_NORMAL,
            'font': ModernTheme.CODE_FONT,
            'height': 8,
            'borderwidth': 0,
            'padx': 5,
            'pady': 5,
            'state': 'normal'
        })
        super().__init__(parent, **kwargs)
        
        self.tag_configure('error', foreground=ModernTheme.ERROR_COLOR)
        self.tag_configure('success', foreground='#4ec9b0')
        
    def write(self, text, tag=None):
        try:
            self.config(state='normal')
            self.insert(tk.END, str(text) + '\n', tag)
            self.see(tk.END)
            self.config(state='disabled')
        except Exception as e:
            print(f"Console write error: {str(e)}")
    
    def clear(self):
        self.config(state='normal')
        self.delete('1.0', tk.END)
        self.config(state='disabled')

class Toolbar(ttk.Frame):
    def __init__(self, parent, commands):
        super().__init__(parent)
        
        buttons = [
            ("Run", "", commands['run']),
            ("Open", "", commands['open']),
            ("Save", "", commands['save']),
            ("Clear", "", commands['clear'])
        ]
        
        for text, icon, command in buttons:
            btn = ttk.Button(
                self,
                text=f"{icon} {text}",
                command=command,
                style='Toolbar.TButton'
            )
            btn.pack(side=tk.LEFT, padx=2)

class AetherIDE:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AetheR IDE")
        self.root.geometry("1200x800")
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind('<Control-q>', self._on_closing)
        self.root.bind('<Control-w>', self._on_closing)
        
        self._setup_styles()
        
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        self.toolbar = Toolbar(main_container, {
            'run': self.run_code,
            'open': self.open_file,
            'save': self.save_file,
            'clear': self.clear_console
        })
        self.toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        paned = ttk.PanedWindow(main_container, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        editor_frame = ttk.Frame(paned)
        paned.add(editor_frame, weight=3)
        
        editor_with_numbers = ttk.Frame(editor_frame)
        editor_with_numbers.pack(fill=tk.BOTH, expand=True)
        
        self.editor = ModernEditor(editor_with_numbers)
        self.line_numbers = LineNumbers(editor_with_numbers, self.editor)
        
        editor_vsb = ModernScrollbar(editor_with_numbers, orient=tk.VERTICAL, command=self.editor.yview)
        editor_hsb = ModernScrollbar(editor_with_numbers, orient=tk.HORIZONTAL, command=self.editor.xview)
        self.editor.configure(yscrollcommand=editor_vsb.set, xscrollcommand=editor_hsb.set)
        
        editor_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        editor_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.console = Console(paned)
        paned.add(self.console, weight=1)
        
        self.status_bar = StatusBar(main_container)
        self.status_bar.pack(fill=tk.X, padx=5, pady=2)
        
        self.root.bind('<Control-r>', lambda e: self.run_code())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        
        self.interpreter = Interpreter()
        self.interpreter.set_output_function(self.console_print)
        
        self._set_example_code()
    
    def _setup_styles(self):
        style = ttk.Style()
        
        style.configure(
            'Toolbar.TButton',
            font=ModernTheme.UI_FONT,
            padding=5
        )
        
        style.configure(
            'Status.TFrame',
            background=ModernTheme.BG_LIGHTER
        )
        style.configure(
            'Status.TLabel',
            background=ModernTheme.BG_LIGHTER,
            foreground=ModernTheme.FG_NORMAL,
            font=ModernTheme.UI_FONT
        )
    
    def _set_example_code(self):
        example = '''// Добро пожаловать в AetheR IDE!
// Нажмите Ctrl+R для запуска кода
// Не забывайте ставить точку с запятой (;) в конце каждой инструкции

'''
        
        self.editor.insert('1.0', example)
        self.editor._highlight_current_line()
    
    def run_code(self):
        self.console.clear()
        print("DEBUG: Starting code execution")
        self.editor.clear_error_highlight()
        source = self.editor.get('1.0', tk.END)
        
        try:
            self.status_bar.set_status("Running...")
            
            try:
                print("DEBUG: Starting lexer")
                lexer = Lexer(source)
                tokens = lexer.scan_tokens()
                print("DEBUG: Lexer completed successfully")
            except LexerError as e:
                print(f"DEBUG: Lexer error caught! Line: {e.line}, Message: {e.message}")
                self.status_bar.set_status("Lexer Error")
                print(f"DEBUG: About to highlight line {e.line}")
                self.editor.highlight_error(e.line)
                print("DEBUG: Line highlighted")
                self.console.write(str(e), 'error')
                return
                
            try:
                print("DEBUG: Starting parser")
                parser = Parser(tokens)
                program = parser.parse()
                print("DEBUG: Parser completed successfully")
            except ParseError as e:
                print(f"DEBUG: Parser error caught! Line: {e.line}, Message: {str(e)}")
                self.status_bar.set_status("Parser Error")
                self.editor.highlight_error(e.line)
                self.console.write(str(e), 'error')
                return
            
            try:
                print("DEBUG: Starting interpreter")
                self.interpreter.interpret(program)
                self.status_bar.set_status("Ready")
                self.console.write("Program completed successfully!", 'success')
                print("DEBUG: Program completed successfully")
            except Exception as e:
                print(f"DEBUG: Runtime error: {str(e)}")
                self.status_bar.set_status("Runtime Error")
                self.console.write(f"Runtime Error: {str(e)}", 'error')
                
        except Exception as e:
            print(f"DEBUG: Internal error: {str(e)}")
            self.status_bar.set_status("Error")
            self.console.write(f"Internal Error: {str(e)}", 'error')
            
    def console_print(self, text):
        self.console.write(text)
    
    def clear_console(self):
        self.console.clear()
        self.status_bar.set_status("Console cleared")
    
    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("AetheR files", "*.aether"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.editor.delete('1.0', tk.END)
                    self.editor.insert('1.0', file.read())
                self.status_bar.set_status(f"Opened {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    
    def save_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".aether",
            filetypes=[("AetheR files", "*.aether"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.editor.get('1.0', tk.END))
                self.status_bar.set_status(f"Saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def _on_closing(self, event=None):
        try:
            self.root.quit()
        except Exception:
            pass
        finally:
            self.root.destroy()
    
    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self._on_closing()

if __name__ == '__main__':
    ide = AetherIDE()
    ide.run()
