import os
import sys
import subprocess
import time
import re
from typing import List, Dict, Set, Optional, Any
from pyzo.qt import QtCore, QtGui, QtWidgets
import pyzo

# ==============================================================================
#  BLOCK   OF AUTONOMOUS   PATHS   AND   ISOLATION   INDICES
# ==============================================================================

CURRENT_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))

STEM_ROOT_DIR = os.path.abspath(os.path.join(CURRENT_TOOL_DIR, '..', '..', '..', '..'))

PORTABLE_ARDUINO_JSON_DIR = os.path.join(CURRENT_TOOL_DIR, 'Arduino')

# Automatically computed path to the portable compiler executable file
PORTABLE_CLI_PATH = os.path.join(STEM_ROOT_DIR, 'ArduinoCLI', 'arduino-cli.exe')
# ==============================================================================

tool_name: str = "Engineering Control Panel"
tool_summary: str = " Universal   remote   control   with  Serial- monitor   and   graphic   plotter ."

class STEMTextHighlighter:
    """ Class ,  highlighting  STEM- constructions   and   register   errors  
    based on a structured JSON dictionary active shell.
    """
    @ classmethod
     def   apply _ highlight ( cls ,  editor :  Any ,  completer _ instance :  Any ) ->  None :
        if not editor or not completer_instance: 
            return
         code_edit = editor._codeEdit if hasattr(editor, '_codeEdit') else editor
        if not hasattr(code_edit, 'setExtraSelections'): 
            return
            
        doc = code_edit.document()
        file_content_raw: str = doc.toPlainText()
        
        # 1.  Attempt   to obtain   a live   runtime dictionary   from   an active  Shell
        sh = pyzo.shells.getCurrentShell()
        keywords_db: Dict[str, Any] = {}
        errors_db: Dict[str, str] = {}
        
        if sh and hasattr(sh, 'get_env'):
            try:
                env = sh.get_env()
                if "__STEM_API__" in env and isinstance(env["__STEM_API__"], dict):
                    keywords_db = env["__STEM_API__"].get("keywords", {})
                    errors_db = env["__STEM_API__"].get("errors", {})
              except Exception:
                 pass
                
        # 2.  FOLBECK - INSURANCE :  If   runtime   is empty ,  load   substructures   from   JSON- autocache
        if not keywords_db:
            cache_data = completer_instance.read_cached_keywords()
            keywords_db = cache_data.get("keywords", {})
            errors_db = cache_data.get("errors", {})
            
        if not keywords_db:
            code_edit.setExtraSelections([])
            return
            
        selections: List[QtWidgets.QTextEdit.ExtraSelection] = []
        
        #  Engineering   formats   colors
         fmt_keyword = QtGui.QTextCharFormat()
        fmt_keyword.setForeground(QtGui.QColor("#00e5ff"))  #  Turquoise
        fmt_keyword.setFontWeight(QtGui.QFont.Weight.Bold)
        
        fmt_const = QtGui.QTextCharFormat()
        fmt_const.setForeground(QtGui.QColor("#ff5252"))     #  Red
        
        fmt_struct = QtGui.QTextCharFormat()
        fmt_struct.setForeground(QtGui.QColor("#ff9100"))    #  Orange
        fmt_struct.setFontWeight(QtGui.QFont.Weight.Bold)
        
        fmt_error_marker = QtGui.QTextCharFormat()
# ffcccc"))  #  Pink   Error Marker
        
         #   We build a map of the exact register based on the keys of the runtime / cache
        exact_case_map: Dict[str, str] = {k.lower(): k for k in keywords_db.keys()}
        
        #   ATOMIC WORD PARSER :   Find single   letter   tokens   of text
        search_expr = QtCore.QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        match_iterator = search_expr.globalMatch(file_content_raw)
        
        while match_iterator.hasNext():
            match_obj = match_iterator.next()
            start_pos = match_obj.capturedStart()
            end_pos = match_obj.capturedEnd()
            actual_token = match_obj.captured()
            pure_lower = actual_token.lower()
            
            #  Checking   explicit   built -in   errors   and   register markers
            is_explicit_error = (actual_token == "Print") or (pure_l ower in errors_db and actual_token != exact_case_map.get(pure_lower))
            is_stem_command = pure_lower in exact_case_map
            
             #   Port constants are always legitimate in uppercase
             is_hardware_constant = actual_token.isupper() and any(p in actual_token  for p in ["M1", "M2", "M3", "M4", "D1", "D2", "A1", "A2", "HIGH", "LOW"])
            
            if not is_stem_command and not is_explicit_error and not is_hardware_constant and actual_token != "print":
                 continue  #  Foreign   word ,  do not   touch
                
            selection = QtWidgets.QTextEdit.ExtraSelection()
            is_wrong_case = False
            
            if is_stem_command and not is_explicit_error and not is_hardware_constant:
                exact_word = exact_case_map[pure_lower]
                if actual_token != exact_word:
                    is_wrong_case = True
                    
            if is_explicit_error or is_wrong_case:
                selection.format = fmt_error_marker  #  Pink   marker   errors !
            else:
                style_word = exact_case_map.get(pure_lower, actual_token)
                if is_hardware_constant or style_word.isupper():
                    selection.format = fmt_const
                elif style_word in ["Serial", "machine", "rp2", " trik", "brick", "FreeCAD", "App", "Gui", "setup", "loop", "GPIO"]:
                    selection.format = fmt_struct
                else:
                    selection.format = fmt_keyword
                    
            selection.cursor = QtGui.QTextCursor(doc)
            selection.cursor.setPosition(start_pos)
            selection.cursor.setPosition(end_pos, QtGui.QTextCursor.MoveMode.KeepAnchor)
            selections.append(selection)
            
        code_edit.setExtraSelections(selections)


class  UniversalSTEMCompleter(QtCore.QObject):
    """ End-to-end   dynamic   compiler ,   working   based   on   the   content   of   JSON cache files ."""
    
    #  Static   fallback - arrays  API  for   microcontrollers   and   engineering   environments
    ARDUINO_API: List[str] = ["pinMode", "digitalWrite", "digitalRead", "analogWrite", "analogRead", "delay", 
                              "delayMicroseconds", "m illis", "micros", "setup", "loop", "Serial", "begin", 
                              "print", "println", "a vailable", "read", "INPUT", "OUTPUT", "HIGH", "LOW", 
                              "INPUT_PULLUP", "LED_BUILTIN"]
                              
    PICO_API: List[str] = ["machine", "Pin", "ADC", "PWM", "I2C", "SPI", "Timer", "time", "sleep", 
                            "sleep_ms", "sleep_u s", "ws2812", "encoder", "IN", "OUT", "PULL_UP", 
"PULL_DOWN", "value",  "toggle", "high", "low", "read_u16", "duty_u16", 
                            "freq", "position", "r p2", "PIO", "asm_pio", "StateMachine", "onewire", 
                            "scan", " ds18x20", "convert_temp", "read_temp"]
                            
    TRIK_API: List[str] = ["trik", "brick", "motor", "sensor", "servo", "encoder", "gyro", "led", 
                            "display", "M1", "M2" , "M3", "M4", "D1", "D2", "A1", "A2", "setPower", 
                            "power", "brake", "read ", "FORWARD", "BACKWARD", "STOP", "BRAKE", "Brick", 
                            "Display" "Gamepad", "Keys", "Led", "LineSensor"]
                            
    GPIO_API: List[str] = ["GPIO", "setmode", "getmode", "setwarnings", "setup", "output", "input", 
                            "cleanup", "PWM", "wait_f or_edge", "add_event_detect", "remove_event_detect", 
                            "event_detected", "B CM", "BOARD", "OUT", "IN", "HIGH", "LOW", "LED", 
                            "Button", "Buzzer", "Motor", "DistanceSensor"]
                            
    FREECAD_API: List[str] = ["FreeCAD", "App", "Gui", "Part", "Mesh", "Draft", "Placement", "Vector", 
"ActiveDocument", "addObjec t", "recompute", "makeBox", "makeCylinder", "makeSphere"]

    def __init__(self, editor: Any, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.editor = editor
        self.code_edit = editor._codeEdit if hasattr(editor, '_codeEdit') else editor
        
        #  Initialize   the standard   compliter   Qt
         self.completer = QtWidgets.QCompleter([], self.code_edit)
        self.completer.setWidget(self.code_edit)
        self.completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated[str].connect(self.insert_completion)
        
        #  Primary   loading   of the current   list   auto-completion
        self.update_completer_model()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if obj != self.code_edit:
            return super().eventFilter(obj, event)
            
        #  Catch   focus   input   tabs ,  to   update   backlight
        if event.type() == QtCore.QEvent.Type.FocusIn:
            self.update_completer_model()
            QtCore.QTimer.singleShot(50, lambda: STEMTextHighlighter.apply_highlight(self.editor, self))
            
        #  When   pressing   keys   we update   markers   in   the code   and   call   the STEM- translator   of hints
        if event.type() == QtCore.QEvent.Type.KeyPress:
            QtCore.QTimer.singleShot(20, lambda: STEMTextHighlighter.apply_highlight(self.editor, self))
            
            tool = pyzo.toolManager.getTool("engineeringpaneltool")
            if tool and hasattr(tool, 'show_stem_educational_tip'):
                QtCore.QTimer.singleShot(30, lambda: tool.show_stem_educational_tip())
                
        return super().eventFilter(obj, event)

    def insert_completion(self, completion: str) -> None:
        if self.completer.widget() != self.code_edit: 
            return
        cursor = self.code_edit.textCursor()
        extra: int = len(completion) - len(self.completer.completionPrefix())
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left)
         cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfWord)
        cursor.insertText(completion[-extra:])
        self.code_edit.setTextCursor(cursor)

    def get_current_cache_filename(self) -> str:
        """ Dynamically   determines   the name of   the JSON file   of the cache   of the active   Pyzo shell ."""
        base_dir: str = CURRENT_TOOL_DIR
        try:
            sh = pyzo.shells.getCurrentShell()
            if not sh: 
                return os.path.join(base_dir, "stem_keywords.json")
            shell_name = str(sh._info.name if hasattr(sh, '_info') else sh.name).lower().strip()
            
            if "arduino" in shell_name: return os.path.join(base_dir, "stem_keywords_arduino.json")
            elif "freecad" in shell_name: return os.path.join(base_dir, "stem_keywords_freecad.json")
            elif " trick " in shell_name or "trik" in shell_name: return os.path.join(base_dir, "stem_keywords_trik.json")
            elif "pico" in shell_name or "micropython" in shell _name: return os.path.join(base_dir, "stem_keywords_pico.json")
            elif "pi" in shell_name: return os.path.join(base_dir, "stem_keywords_pi.json")
        except Exception:
            pass
        return os.path.join(base_dir, "stem_keywords.json")

    def read_cached_keywords(self) -> Dict[str, Any]:
         """ Reads   a structured   database   STEM   API   from   a JSON file   cache ."""
        import json
        cache_file = self.get_current_cache_filename()
        if not os.path.exists(cache_file): 
            return {}
        try:
            with open(cache_file, 'r', encoding='utf-8') as f: 
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        #  Replace   general  Exception  with   two   specific   classes   of   exceptions
         except (OSError, json.JSONDecodeError) as e:
            print(f"[ Error   reading  JSON- cache ]: {e}", file=sys.stderr)
            return {}

    def update_completer_model(self) -> None:
        """ Dynamically   updates   the list   of   QCompleter   words   based   on   the extracted   JSON keys . """
        cache_data = self.read_cached_keywords()
        keywords_db = cache_data.get("keywords", {})
        
        #  Extract   legitimate  STEM- commands   of the current   environment
        completion_words = list(keywords_db.keys())
        
        #  FOLBECK - INSURANCE :  If  JSON  has not yet   been   created   by the start   script ,  we take   the internal   arrays
        if not completion_words:
            cache_file = self.get_current_cache_filename()
            if "arduino" in cache_file: completion_words = self.ARDUINO_API.copy()
            elif "freecad" in cache_file: completion_words = self.FREECAD_API.copy()
            elif "trik" in cache_file: completion_words = self.TRIK_API.copy()
            elif "pico" in cache_file: completion_words = self.PICO_API.copy()
            elif "pi" in cache_file: completion_words = self.GPIO_API.copy()
        
        if "print" not in completion_words and completion_words:
            completion_words.append("print")
            
        #   Rolling out a string model in Qt
        model = QtCore.QStringListModel(completion_words, self.completer)
        self.completer.setModel(model)

def apply_stem_extensions_to_panel(tool_instance: Any) -> None:
    if not tool_instance: return
    try:
        sh = pyzo.shells.getCurrentShell()
        if not sh:
            tool_instance._row1_widget.hide()
             tool_instance._row2_widget.hide()
            tool_instance.display_stack.hide()
            if hasattr(tool_instance, 'btn_ssh'): tool_instance.btn_ssh.hide()
            if hasattr(tool_instance, 'lbl_ip'): tool_instance.lbl_ip.hide()
            if hasattr(tool_instance, 'txt_ip'): tool_instance.txt_ip.hide()
            if hasattr(tool_instance, 'lbl_password'): tool_instance.lbl_password.hide()
            if hasattr(tool_instance, 'txt_password'): tool_instance.txt_password.hide()
            if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.hide()
            return
            
        shell_name: str = ""
        if hasattr(sh, '_info') and sh._info and hasattr(sh._info, 'name') and sh._info.name:
            shell_name = str(sh._info.name).lower().strip()
        elif hasattr(sh, 'name') and sh.name:
            shell_name = str(sh.name).lower().strip()
            
        if hasattr(tool_instance, 'btn_ssh'): tool_instance.btn_ssh.hide()
        if hasattr(tool_instance, 'lbl_ip'): tool_instance.lbl_ip.hide()
        if hasattr(tool_instance, 'txt_ip'): tool_instance.txt_ip.hide()
        if hasattr(tool_instance, 'lbl_password'): tool_instance.lbl_password.hide()
        if hasattr(tool_instance, 'txt_password'): tool_instance.txt_password.hide()
        
        tool_instance.setMinimumHeight(0)
        tool_instance.setMaximumHeight(16777215)
        
        parent_dock = tool_instance.parentWidget()
        while parent_dock and not parent_dock.inherits("QDockWidget"):
            parent_dock = parent_dock.parentWidget()
            
        if "freecad" not in shell_name and parent_dock and not parent_dock.isVisible():
            parent_dock.show()
            
        # ---  SYNCHRONOUS   AUTOLOOP   TIMER   FOR   ENVIRONMENTS  ---
        if "freecad" in shell_name:
             tool_instance._row1_widget.hide()
            tool_instance._row2_widget.hide()
            tool_instance.display_stack.hide()
            if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.hide()
            if parent_dock: parent_dock.hide()
            else: tool_instance.setFixedHeight(0)
            
        elif "arduino" in shell_name:
            tool_instance._row1_widget.show()
            tool_instance.lbl_board.show()
            tool_instance.combo_boards.show()
            tool_instance.btn_refresh.show()
            if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.show()
            tool_instance.lbl_port.show()
            tool_instance._row2_widget.show()
            tool_instance.display_stack.show()
            tool_instance.btn_f5.show()          
            tool_instance.btn_f6.show()          
            tool_instance.btn_monitor.show()
            tool_instance.btn_mode_toggle.show()
            tool_instance.btn_baud_toggle.show()
            tool_instance.combo_time_base.show()
            if hasattr(tool_instance, 'scan_installed_cli_boards'):
                tool_instance.scan_installed_cli_boards()
                
        elif " trick " in shell_name or "trik" in shell_name:
            tool_instance._row1_widget.hide()   
            tool_instance._row2_widget.show()   
            tool_instance.display_stack.show()  
            tool_instance.btn_f5.hide()         
            tool_instance.btn_f6.hide()         
            tool_instance.btn_monitor.show()    
            tool_instance.btn_mode_toggle.show()
            tool_instance.btn_baud_toggle.show()
             tool_instance.combo_time_base.show()
            if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.hide()
            
        elif "pi" in shell_name or "pico" in shell_name or "micropython" in shell_name:
            if "pico" in shell_name or "micropython" in shell_name:
                tool_instance._row1_widget.hide()   
                tool_instance._row2_widget.show()
                tool_instance.display_stack.show()
                tool_instance.btn_f5.hide()
                tool_instance.btn_f6.hide()         
                tool_instance.btn_monitor.show()
                tool_instance.btn_mode_toggle.show()
                tool_instance.btn_baud_toggle.show()
                tool_instance.combo_time_base.show()
                if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.hide()
            else:
                #  TIMER SCRIPT FOR NETWORK   RASPBERRY   PI
                tool_instance._row1_widget.show()
                tool_instance.lbl_board.hide()
                tool_instance.combo_boards.hide()
                tool_instance.btn_refresh.hide()
                tool_instance.lbl_port.hide()
                if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.hide()
                
                if hasattr(tool_instance, 'lbl_ip'): tool_instance.lbl_ip.show()
                if hasattr(tool_instance, 'txt_ip'): tool_instance.txt_ip.show()
                if hasattr(tool_instance, 'lbl_password'): tool_instance.lbl_password.show()
                if hasattr(tool_instance, 'txt_password'): tool_instance.txt_password.show()
                if hasattr(tool_instance, 'btn_ssh'): tool_instance.btn_ssh.show()
                
                tool_instance._row2_widget.hide()   
                tool_instance.display_stack.hide()  
                tool_instance.setFixedHeight(35)
                if parent_dock:
                     parent_dock.resize(parent_dock.width(), 35)
        else:
            tool_instance._row1_widget.hide()
            tool_instance._row2_widget.hide()
            tool_instance.display_stack.hide()
            if hasattr(tool_instance, 'btn_lib_manager'): tool_instance.btn_lib_manager.hide()
            
        if "freecad" not in shell_name:
            if not ("pi" in shell_name and "pico" not in shell_name and "micropython" not in shell_name):
                tool_instance.setMaximumHeight(16777215)
                if tool_instance.height() < 50:
                    tool_instance.setMinimumHeight(65)
                    if parent_dock:
                        parent_dock.resize(parent_dock.width(), 180)
                        
        ed = pyzo.editors.getCurrentEditor()
        if ed and hasattr(ed, 'filename') and ed.filename:
            filename: str = ed.filename.lower()
            if filename.endswith('.ino') and hasattr(ed, 'setParser'): ed.setParser('c')
            code_edit_widget = ed._codeEdit if hasattr(ed, '_codeEdit') else ed
            if not hasattr(ed, '_universal_stem_filter'):
                ed._universal_stem_filter = UniversalSTEMCompleter(ed)
                code_edit_widget.installEventFilter(ed._universal_stem_filter)
                
            STEMTextHighlighter.apply_highlight(ed, ed._universal_stem_filter)
            if hasattr(tool_instance, 'show_stem_educational_tip'):
                tool_instance.show_stem_educational_tip()
                
    except Exception as e:
        print(f"[ Critical   panel   update   failure ]: {e}", file=sys.stderr)

def inject_stem_editor_extensions() -> None:
    pass

class  ArduinoPlotterWidget(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.points: List[float] = [] 
        self.timestamps: List[float] = [] 
        self.max_points: int = 500 
        self.setStyleSheet("background-color: #1e1e1e;")
        self.time_window: float = 5.0 
        self.start_time: Optional[float] = None 
        self.current_time_axis: float = 0.0
        
        self.animate_timer = QtCore.QTimer(self)
        self.animate_timer.timeout.connect(self.tick_animation)
 
    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if self.start_time is None:
            self.start_time = time.perf_counter()
        self.animate_timer.start(16) 
 
    def tick_animation(self) -> None:
        if self.isVisible():
            if self.start_time is not None:
                self.current_time_axis = time.perf_counter() - self.start_time
            self.update() 
        else:
            self.animate_timer.stop()

    def set_time_window(self, seconds: float) -> None:
        self.time_window = float(seconds)
        self.update()

    def add_value(self, value: float) -> None:
        try:
             if self.start_time is None:
                self.start_time = time.perf_counter()
            sample_time: float = time.perf_counter() - self.start_time
            self.blockSignals(True)
            self.points.append(float(value))
            self.timestamps.append(sample_time) 
            if len(self.points) > self.max_points:
                self.points.pop(0)
                self.timestamps.pop(0)
            self.blockSignals(False)
        except ValueError:
            pass

    def clear_graph(self) -> None:
        self.points.clear()
        self.timestamps.clear()
        self.start_time = None
        self.current_time_axis = 0.0
        self.update()
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        pad_left, pad_bottom, pad_top, pad_right = 60, 30, 20, 20
        plot_w: int = w - pad_left - pad_right
        plot_h: int = h - pad_top - pad_bottom
        if plot_w <= 0 or plot_h <= 0:
            return
            
        pen_axes = QtGui.QPen(QtGui.QColor("#666666"), 1)
        pen_axes.setCosmetic(True)
        pen_grid = QtGui.QPen(QtGui.QColor("#242424"), 1, QtCore.Qt.PenStyle.SolidLine)
        pen_grid.setCosmetic(True)
        
         #   The grid is drawn without aliasing for clarity in 1 pixel
         painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        painter.setPen(pen_axes)
        painter.drawRect(pad_left, pad_top, plot_w, plot_h)
 
        #  Copy   collections   to   prevent   IndexError  due to   asynchronous   modification
        local_points = list(self.points)
        local_timestamps = list(self.timestamps)

        if local_points:
            min_val: float = min(local_points)
            max_val: float = max(local_points)
            val_range: float = max_val - min_val
            if val_range == 0.0:
                val_range = 1.0
                max_val += 0.5
                 min_val -= 0.5
        else:
            min_val, max_val, val_range = -1.0, 1.0, 2.0
 
        painter.setFont(QtGui.QFont("Consolas", 8))
        for i in range(4):
            ratio: float = i / 3.0
            y_pos: int = h - pad_bottom - int(ratio * plot_h)
            if 0 < i < 3:
                painter.setPen(pen_grid)
                painter.drawLine(pad_left, y_pos, w - pad_right, y_pos)
            current_y_val: float = min_val + (ratio * val_range)
            painter.setPen(QtGui.QColor("#aaaaaa"))
            painter.drawText(5, y_pos + 4, f"{current_y_val:>8.2f}")
 
        t_max: float = self.current_time_axis
        t_min: float = max(0.0, t_max - self.time_window)
        t_range: float = t_max - t_min if (t_max - t_min) > 0.0 else 1.0
 
         if self.time_window <= 1.0:
            grid_step = 0.2 
            str_format = "{:.1f}s"
        elif self.time_window <= 3.0:
            grid_step = 0.5 
            str_format = "{:.1f}s"
        elif self.time_window <= 10.0:
            grid_step = 1.0 
            str_format = "{:.0f}s"
        else:
            grid_step = 5.0 
            str_format = "{:.0f}s"
 
        # Protection against split to zero when calculating ticks
        start_tick: float = (int(t_min / grid_step) + 1) * grid_step if grid_step != 0.0 else t_min
        painter.setClipRect(pad_left + 1, pad_top + 1, plot_w - 1, plot_h - 1)
 
        curr_tick: float = start_tick
        while curr_tick <= t_max:
            norm_x: float = (curr_tick - t_min) / t_range
            x_pos: int = pad_left + int(norm_x * plot_w)
            if pad_left < x_pos < (w - pad_right):
                painter.setPen(pen_grid)
                painter.drawLine(x_pos, pad_top, x_pos, h - pad_bottom)
                painter.save()
                painter.setClipping(False)
                painter.setPen(QtGui.QColor("#aaaaaa"))
                painter.drawText(x_pos - 15, h - pad_bottom + 15, str_format.format(curr_tick))
                painter.restore()
            curr_tick += grid_step
 
        # The graph is displayed with smoothing
        if local_points:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
             pen_line = QtGui.QPen(QtGui.QColor("#00ff00"), 2, QtCore.Qt.PenStyle.SolidLine)
            painter.setPen(pen_line)
            path = QtGui.QPainterPath()
            first_point: bool = True
            for i in range(len(local_points)):
                t_point: float = local_timestamps[i]
                if t_point < t_min:
                     continue 
                norm_x = (t_point - t_min) / t_range
                x: float = pad_left + (norm_x * plot_w)
                norm_y: float = (local_points[i] - min_val) / val_range
                y: float = h - pad_bottom - (norm_y * plot_h)
                if first_point:
                    path.moveTo(x, y)
                     first_point = False
                else:
                    path.lineTo(x, y)
            if not path.isEmpty():
                painter.drawPath(path)
class EngineeringPanelTool(QtWidgets.QWidget):
    tool_name: str = "Engineering Control Panel"
    tool_summary: str = "Universal control with Serial monitor and graphic plotter."

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tool_name)
        
        self.CLI_PATH: str = PORTABLE_CLI_PATH
        self.TARGET_SHELL_NAME: str = 'Arduino C++'
        self.current_com_port: Optional[str] = None
        self.serial_port: Any = None 
        
        self.CORE_BOARDS: Dict[str, str] = {
            "Arduino Leonardo": "arduino:avr:leonardo",
             "Arduino Mega 2560": "arduino:avr:mega",
            "Arduino Nano (New Bootloader)": "arduino:avr:nano",
            "Arduino Nano (Old Bootloader)": "arduino:avr:nano:cpu=atmega328old",
            "Arduino Uno": "arduino:avr:uno",
            "ESP32 Dev Module": "esp32:esp32:esp32",
            "NodeMCU 32S (ESP32)": "esp32:esp32:nodemcu-32s",
            "Raspberry Pi Pico": "rp2040:rp2040:rp2040"
        }
        self.BOARDS: Dict[str, str] = self.CORE_BOARDS.copy()
        
        self._main_layout = QtWidgets.QVBoxLayout(self)
        self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._main_layout.setSpacing(4)
        self.setLayout(self._main_layout)
        
        # --- LINE 1 PANEL (Hardware and Network Settings) ---
        self._row1_widget = QtWidgets.QWidget()
        self._row1_layout = QtWidgets.QHBoxLayout(self._row1_widget)
        self._row1_layout.setContentsMargins(0, 0, 0, 0)
        self._row1_layout.setSpacing(4)
        
        self.lbl_board = QtWidgets.QLabel(text='<b>Board:</b>')
        self._row1_layout.addWidget(self.lbl_board)
        
        self.combo_boards = QtWidgets.QComboBox()
        self.combo_boards.setMaxVisibleItems(15)
        self.combo_boards.addItems(list(self.CORE_BOARDS.keys()))
        self.combo_boards.currentTextChanged.connect(self.sync_hardware_settings)
        self._row1_layout.addWidget(self.combo_boards)

        self.btn_lib_manager = QtWidgets.QPushButton(text='Libraries')
        self.btn_lib_manager.setStyleSheet("background-color: #007acc; color: white; font-weight: bold;")

        self.btn_lib_manager.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
         self.btn_lib_manager.setMinimumSize(0, 0)

        self.btn_lib_manager.clicked.connect(self.open_library_manager)
        self._row1_layout.addWidget(self.btn_lib_manager)
        
        self.btn_refresh = QtWidgets.QPushButton(text='Find port')
        self.btn_refresh.clicked.connect(self.sync_hardware_settings)
        self._row1_layout.addWidget(self.btn_refresh)
        
        self.lbl_port = QtWidgets.QLabel(text='<b>Port:</b> Search... ')
        self._row1_layout.addWidget(self.lbl_port)
        
        # Network Authorization Widgets for Raspberry Pi
        self.lbl_ip = QtWidgets.QLabel(text='<b>IP address Pi:</b>')
        self._row1_layout.addWidget(self.lbl_ip)
        self.txt_ip = QtWidgets.QLineEdit()
        self.txt_ip.setPlaceholderText("192.168.1.100")
        self.txt_ip.setText("192.168.1.100")
        self.txt_ip.setFixedWidth(110)
        self._row1_layout.addWidget(self.txt_ip)
        
        self.lbl_password = QtWidgets.QLabel(text='<b>Password:</b>')
        self._row1_layout.addWidget(self.lbl_password)
        self.txt_password = QtWidgets.QLineEdit()
        self.txt_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("raspberry")
        self.txt_password.setText("raspberry")
        self.txt_password.setFixedWidth(90)
        self._row1_layout.addWidget(self.txt_password)
        self.btn_ssh = QtWidgets.QPushButton(text='Run on Pi via SSH')
        self.btn_ssh.setStyleSheet("background-color: #8a2be2; color: white; font-weight: bold;")
        self.btn_ssh.clicked.connect(self.run_remote_ssh_code)
        self._row1_layout.addWidget(self.btn_ssh)
        self.lbl_ip.hide()
         self.txt_ip.hide()
        self.lbl_password.hide()
        self.txt_password.hide()
        self.btn_ssh.hide()
        self._row1_layout.addStretch()
        self._main_layout.addWidget(self._row1_widget)
        
        # --- ROW 2 PANELS (Tools control and debugging Arduino/Pico) ---
        self._row2_widget = QtWidgets.QWidget()
        self._row2_layout = QtWidgets.QHBoxLayout(self._row2_widget)
        self._row2_layout.setContentsMargins(0, 0, 0, 0)
        self._row2_layout.setSpacing(4)
        
        self.btn_f5 = QtWidgets.QPushButton(text='Check')
        self.btn_f5.clicked.connect(self.build_code)
        self._row2_layout.addWidget(self.btn_f5)
        
        self.btn_f6 = QtWidgets.QPushButton(text='Flash')
        self.btn_f6.clicked.connect(self.upload_code)
        self._row2_layout.addWidget(self.btn_f6)
        
        self.btn_monitor = QtWidgets.QPushButton(text='Monitor')
        self.btn_monitor.setCheckable(True)
        self.btn_monitor.toggled.connect(self.toggle_serial_monitor)
        self._row2_layout.addWidget(self.btn_monitor)
        
        self.btn_mode_toggle = QtWidgets.QPushButton(text='Graph')
        self.btn_mode_toggle.setCheckable(True)
        self.btn_mode_toggle.clicked.connect(self.switch_display_mode)
        self._row2_layout.addWidget(self.btn_mode_toggle)
        
        self.current_baud_index: int = 0
        baud_setup_string: str = "9600,115200,57600,38400,19200,4800"
        self.BAUD_RATES: List[int] = [int(x) for x in baud_setup_string.split(",")]
         self.btn_baud_toggle = QtWidgets.QPushButton(text=f"{self.BAUD_RATES[self.current_baud_index]}")
        self.btn_baud_toggle.clicked.connect(self.cycle_baud_rate)
        self._row2_layout.addWidget(self.btn_baud_toggle)
        
        self.combo_time_base = QtWidgets.QComboBox()
        self.combo_time_base.addItems(["1.0s", "3.0s", "5.0s", "10.0s", "30.0s"])
        self.combo_time_base.setCurrentText("5.0s")
        self.combo_time_base.currentTextChanged.connect(self.change_plotter_time_base)
        self._row2_layout.addWidget(self.combo_time_base)
        
        self._row2_layout.addStretch()
        self._main_layout.addWidget(self._row2_widget)
        
        # --- CENTRAL PANEL ---
        self.display_stack = QtWidgets.QStackedWidget()
        self.txt_monitor = QtWidgets.QTextEdit()
        self.txt_monitor.setReadOnly(True)
        self.txt_monitor.setPlaceholderText("Data from the microcontroller is not receiving.")
        self.txt_monitor.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas, Monaco, monospace;")
        self.display_stack.addWidget(self.txt_monitor)
        
        self.plotter_widget = ArduinoPlotterWidget()
        self.display_stack.addWidget(self.plotter_widget)
        self._main_layout.addWidget(self.display_stack)
        
        # PRESS TO THE UPPER EDGE
        self._main_layout.addStretch(1)
        
        self.serial_timer: Optional[QtCore.QTimer] = None 
        
        self._row1_widget.hide()
        self._row2_widget.hide()
        self.display_stack.hide()

        self._stem_autoloop = QtCore.QTimer(self)
        self._stem_autoloop.timeout.connect(lambda: apply_stem_extensions_to_panel(self))
        self._stem_autoloop.start(300)
        
        if hasattr(pyzo, "shells") and pyzo.shells:
            try:
                pyzo.shells.currentShellChanged.connect(self.update_panel_view)
                self.update_panel_view(pyzo.shells.getCurrentShell())
            except AttributeError as e:
                print(f"[Panel Crash Subscriptions Shell]: {e}", file=sys.stderr)
                
        QtCore.QTimer.singleShot(500, self.scan_installed_cli_boards)

    def open_library_manager(self) -> None:
        """Opens the Arduino CLI Library Manager dialog box."""
        dialog = ArduinoLibraryManagerDialog(self.CLI_PATH, self)
        dialog.exec()

    def update_panel_view(self, shell: Any = None) -> None:
        if not shell:
            self._row1_widget.hide()
            self._row2_widget.hide()
            self.display_stack.hide()
            return
            
        shell_name: str = ""
        if hasattr(shell, '_info') and shell._info and hasattr(shell._info, 'name') and shell._info.name:
            shell_name = str(shell._info.name).lower().strip()
        elif hasattr(shell, 'name') and shell.name:
            shell_name = str(shell.name).lower().strip()
            
        print(f"DEBUG: Active shell name is '{shell_name}'")
        
         # RELIEVING PORTS WHEN CHANGING SHELLS
        if "arduino" not in shell_name and self.btn_monitor.isChecked():
            print("DEBUG: Automatic releasing COM-port for third-party environment")
            self.stop_monitor_internally()
        
        if hasattr(self, 'btn_ssh'): self.btn_ssh.hide()
        if hasattr(self, 'lbl_ip'): self.lbl_ip.hide()
        if hasattr(self, 'txt_ip'): self.txt_ip.hide()
        if hasattr(self, 'lbl_password'): self.lbl_password.hide()
        if hasattr(self, 'txt_password'): self.txt_password.hide()
        
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        parent_dock = self.parentWidget()
        while parent_dock and not parent_dock.inherits("QDockWidget"):
            parent_dock = parent_dock.parentWidget()
            
        if "freecad" not in shell_name and parent_dock and not parent_dock.isVisible():
            parent_dock.show()
            
        # --- LOGIC ISOLATION ELEMENTS IN INTERFACE ---
        if "arduino" in shell_name:
            self._row1_widget.show()
            self._row2_widget.show()
            self.display_stack.show()
            
            self.lbl_board.show()
            self.combo_boards.show()
            self.btn_refresh.show()
            self.btn_lib_manager.show()
            self.lbl_port.show()
            
            self.btn_f5.show()
            self.btn_f6.show()
             self.btn_monitor.show()
            self.btn_mode_toggle.show()
            self.btn_baud_toggle.show()
            self.combo_time_base.show()
            if hasattr(self, 'scan_installed_cli_boards'):
                self.scan_installed_cli_boards()
                
        elif "trick" in shell_name or "trik" in shell_name:
            self._row1_widget.hide()
            self._row2_widget.show()
            self.display_stack.show()
            self.btn_f5.hide()
            self.btn_f6.hide()
            self.btn_monitor.show()
            self.btn_mode_toggle.show()
            self.btn_baud_toggle.show()
            self.combo_time_base.show()
            if hasattr(self, 'btn_lib_manager'): self.btn_lib_manager.hide()
            
        elif "pi" in shell_name or "pico" in shell_name or "micropython" in shell_name:
            if "pico" in shell_name or "micropython" in shell_name:
                self._row1_widget.hide()
                self._row2_widget.show()
                self.display_stack.show()
                self.btn_f5.hide()
                self.btn_f6.hide()
                self.btn_monitor.show()
                self.btn_mode_toggle.show()
                self.btn_baud_toggle.show()
                self.combo_time_base.show()
                if hasattr(self, 'btn_lib_manager'): self.btn_lib_manager.hide()
            else:
                self._row1_widget.show()
                self.lbl_board.hide()
                 self.combo_boards.hide()
                self.btn_refresh.hide()
                self.btn_lib_manager.hide()
                self.lbl_port.hide()
                
                if hasattr(self, 'lbl_ip'): self.lbl_ip.show()
                if hasattr(self, 'txt_ip'): self.txt_ip.show()
                if hasattr(self, 'lbl_password'): self.lbl_password.show()
                if hasattr(self, 'txt_password'): self.txt_password.show()
                if hasattr(self, 'btn_ssh'): self.btn_ssh.show()
                
                self._row2_widget.hide()
                self.display_stack.hide()
                self.setFixedHeight(35)
                if parent_dock:
                    parent_dock.resize(parent_dock.width(), 35)
                    
        elif "freecad" in shell_name:
            self._row1_widget.hide()
            self._row2_widget.hide()
            self.display_stack.hide()
            self.btn_lib_manager.hide()
            if parent_dock: parent_dock.hide()
            else: self.setFixedHeight(0)
        else:
            self._row1_widget.hide()
            self._row2_widget.hide()
            self.display_stack.hide()
            self.btn_lib_manager.hide()
            
        if "freecad" not in shell_name and "pico" not in shell_name and "micropython" not in shel l_name and "arduino" not in shell_name and "trick" not in shell_name and "trik" not in shell_name:
            pass
        else:
             if not ("pi" in shell_name and "pico" not in shell_name and "micropython" not in shell_name):
                self.setMaximumHeight(16777215)
                if self.height() < 50:
                    self.setMinimumHeight(65)
                    if parent_dock:
                        parent_dock.resize(parent_dock.width(), 180)

    def scan_installed_cli_boards(self) -> None:
        if not os.path.exists(self.CLI_PATH):
            return
        try:
            sh = pyzo.shells.getCurrentShell()
            shell_name: str = sh._info.name.lower()  if (sh and hasattr(sh, '_info') and sh._info) else ""
            if "arduino" not in shell_name:
                 return 
            if hasattr(self, '_cli_boards_cached') and getattr(self, '_cli_boards_cached'):
                 return
                
            cmd_cores: str = f'"{self.CLI_PATH}" core list'
            out_cores: str = subprocess.check_output(cmd_cores, shell=True, text=True, errors='ignore')
            
            installed_ids: Set[str] = set()
            for line in out_cores.split('\n'):
                clean_line: str = line.strip()
                if not clean_line or "ID" in clean_line or "Version" in clean_line:
                      continue
                parts: List[str] = [p.strip() for p in clean_line.split(' ') if p.strip()]
                 if parts:
                    installed_ids.add(parts[0])
                    
            filtered_boards: Dict[str, str] = {}
            for human_name, fqbn in self.CORE_BOARDS.items():
                core_prefix: str = ":".join(fqbn.split(":")[:2])
                if core_prefix in installed_ids:
                     filtered_boards[human_name] = fqbn
            self.BOARDS = filtered_boards if filtered_boards else self.CORE_BOARDS.copy()
            
            self._cli_boards_cached = True
            self.combo_boards.blockSignals(True)
            current_selection: str = self.combo_boards.currentText()
            self.combo_boards.clear()
            self.combo_boards.addItems(sorted(list(self.BOARDS.keys())))
            
            idx: int = self.combo_boards.findText(current_selection)
            self.combo_boards.setCurrentIndex(idx if idx >= 0 else 0)
            self.combo_boards.blockSignals(False)
        except (subprocess.SubprocessError, OSError, AttributeError) as e:
            print(f"[Error setting up list of boards via CLI]: {e}", file=sys.stderr)
    def detect_com_port(self) -> Optional[str]:
        try:
            if CURRENT_TOOL_DIR not in sys.path:
                sys.path.insert(0, CURRENT_TOOL_DIR)
            
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            for port in ports:
                desc: str = port.description.lower()
                hwid: str = port.hwid.lower()
                if any(x in desc or x in hwid for x in  ["arduino", "ch340", "cp210", "ftdi", "usb serial"]):
                    return str(port.device)
            for port in ports:
                if port.device not in ["COM1", "COM2"]: 
                    return str(port.device)
             return None
        except Exception as e:
            print(f"[COM port detection error]: {e}", file=sys.stderr)
             return None

     def sync_hardware_settings(self) -> None:
        detected_port: Optional[str] = self.detect_com_port()
        self.current_com_port = detected_port
        selected_human_name: str = self.combo_boards.currentText()
        fqbn: str = self.BOARDS.get(selected_human_name, "arduino:avr:uno")
        
        if detected_port:
            self.lbl_port.setText(f' <b>Port:</b> <span style="color:green;">{detected_port}</span> ')
        else:
            self.lbl_port.setText(' <b>Port:</b> <span style="color:red;">Not found</span> ')
        
        try:
            sh = pyzo.shells.getCurrentShell()
            if sh and hasattr(sh, '_info') and sh._info.name == self.TARGET_SHELL_NAME:
                # BATCH LAUNCH: Combine commands into one block to protect from UI freezes
                port_cmd = f"COM_PORT = '{detected_port}'" if detected_port else "COM_PORT = None"
                setup_payload = (
                    f"CLI_PATH = r'{self.CLI_PATH}'\n"
                    f"BOARD_TYPE = '{fqbn}'\n"
                    f"{port_cmd}"
                )
                sh.executeCommand(setup_payload)
        except AttributeError as e:
            print(f"[Hardware sync error]: {e}", file=sys.stderr)

    def fix_sketch_folder_structure(self, ed: Any) -> str:
        if not ed or not ed.filename:
            return ""
        
        current_path: str = str(ed.filename)
        current_dir: str = os.path.dirname(current_path)
        file_name: str = os.path.basename(current_path)
        base_name, ext = os.path.splitext(file_name)
        
         if ext.lower() == '.ino' and os.path.basename(current_dir) != base_name:
            new_project_dir: str = os.path.join(current_dir, base_name)
            new_file_path: str = os.path.join(new_project_dir, file_name)
            
            try:
                ed.save() 
                QtWidgets.QMessageBox.information(
                      self,
                    "Arduino sketch structure rule",
                    f"The sketch file should be located in the folder right but with the same name.\nThe folder '{base_name}' was created automatically.",
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                os.makedirs(new_project_dir, exist_ok=True)
                text_content: str = ed.toPlainText() if hasattr(ed, 'toPlainText') else ed.text()
                with open(new_file_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                
                if hasattr(ed, 'setFilename'):
                    ed.setFilename(new_file_path)
                elif hasattr(ed, '_filename'):
                    ed._filename = new_file_path
                
                if hasattr(ed, 'sigFilenameChanged'):
                    ed.sigFilenameChanged.emit(new_file_path)
                
                if os.path.exists(current_path):
                     try: 
                        os.remove(current_path)
                      except OSError: 
                         pass
                
                QtWidgets.QApplication.processEvents()
                return new_file_path
             except (OSError, IOError) as e:
                print(f"[Error working with STEM file system]: {e}", file=sys.stderr)
        return current_path

    def build_code(self) -> None:
        self.stop_monitor_internally()
        ed = pyzo.editors.getCurrentEditor()
        if not ed or not ed.filename: 
            return
        
        filename_lower: str = ed.filename.lower()
        sh = pyzo.shells.getCurrentShell()
        if not sh: 
            return
        
        if filename_lower.endswith('.ino'):
            target_file_path: str = self.fix_sketch_folder_structure(ed)
            if not target_file_path: 
                 return
            
            selected_human_name: str = self.combo_boards.currentText()
            fqbn: str = self.BOARDS.get(selected_human_name, "arduino:avr:uno")
            board_folder_name: str = fqbn.replace(':', '.').replace('=', '.')
            project_dir: str = os.path.dirname(target_file_path)
            build_dir: str = os.path.join(project_dir, "build", board_folder_name)
            os.makedirs(build_dir, exist_ok=True)
            
            # Forwarding the compiler dynamic path to runtime Shell
            sh.executeCommand(f"CLI_PATH = r'{self.CLI_PATH}'")
            sh.executeCommand(f"import os; os.environ['PYZO_ACTIVE_FILE'] = r'{target_file_path}'")
            sh.executeCommand(f"os.environ['ARDUINO_BUILD_PATH'] = r'{build_dir}'")
            self.sync_hardware_settings()
            sh.executeCommand("build()")
        elif filename_lower.endswith('.py'):
             ed.save()
            self.txt_monitor.append("<span style='color:yellow;'>[MicroPython]: Parse analysis...<br>")
            sh.executeCommand(f"exec(open(r'{ed.filename}', encoding='utf-8').read())")

    def upload_code(self) -> None:
        self.stop_monitor_internally()
        ed = pyzo.editors.getCurrentEditor()
        if not ed or not ed.filename: 
            return
        
        filename_lower: str = ed.filename.lower()
        sh = pyzo.shells.getCurrentShell()
        if not sh: 
            return
        
        if filename_lower.endswith('.ino'):
            target_file_path: str = self.fix_sketch_folder_structure(ed)
            if not target_file_path: 
                 return
            
            selected_human_name: str = self.combo_boards.currentText()
            fqbn: str = self.BOARDS.get(selected_human_name, "arduino:avr:uno")
            board_folder_name: str = fqbn.replace(':', '.').replace('=', '.')
            project_dir: str = os.path.dirname(target_file_path)
            build_dir: str = os.path.join(project_dir, "build", board_folder_name)
            os.makedirs(build_dir, exist_ok=True)
            
            # Forwarding the compiler dynamic path to runtime Shell
            sh.executeCommand(f"CLI_PATH = r'{self.CLI_PATH}'")
            sh.executeCommand(f"import os; os.environ['PYZO_ACTIVE_FILE'] = r'{target_file_path}'")
            sh.executeCommand(f"os.environ['ARDUINO_BUILD_PATH'] = r'{build_dir}'")
            self.sync_hardware_settings()
            sh.executeCommand("upload()")
        elif filename_lower.endswith('.py'):
             ed.save()
            self.txt_monitor.append("<span style='color:cyan;'>[MicroPython]: Write to memory Pi Pico...<br>")
            if self.current_com_port:
                 try:
                    with open(ed.filename, 'r', encoding='utf-8') as f:
                        file_content: str = f.read().replace("'", "\\'")
                    remote_write_cmd: str = f"with o pen('main.py', 'w') as f: f.write('{file_content}')"
                    sh.executeCommand(f"send('{remote_write_cmd}')")
                    sh.executeCommand("send('\x04')") 
                    self.txt_monitor.append("<span style='color:green;'>[Success]: File main.py saved!<br>")
                except IOError as e:
                    self.txt_monitor.append(f"<span style='color:red;'>[I/O Error]: {e}<br>")
            else:
                self.txt_monitor.append("<span style='color:red;'>[Error]: Board port not found!<br>")

    def switch_display_mode(self) -> None:
        if self.btn_mode_toggle.isChecked():
            self.btn_mode_toggle.setText("Text")
            self.display_stack.setCurrentIndex(1) 
        else:
            self.btn_mode_toggle.setText("Graphic")
            self.display_stack.setCurrentIndex(0) 

    def change_plotter_time_base(self, text: str) -> None:
        if hasattr(self, 'plotter_widget') and self.plotter_widget:
            try:
                seconds: float = float(text.replace("s", ""))
                self.plotter_widget.set_time_window(seconds)
            except ValueError:
                 pass

    def cycle_baud_rate(self) -> None:
        self.current_baud_index = (self.current_baud_index + 1) % len(self.BAUD_RATES)
        new_baud: int = self.BAUD_RATES[self.current_baud_index]
         self.btn_baud_toggle.setText(f"{new_baud}")
        if hasattr(self, 'serial_port') and self.serial_port and getattr(self.serial_port, 'is_open', False):
            try:
                self.serial_port.baudrate = new_baud
                 self.txt_monitor.append(f"<span style='color:cyan;'>[Toggle]: Speed changed to {new_baud} baud.</span><br>")
            except Exception as e:
                print(f"[Speed switching error]: {e}", file=sys.stderr)

    def toggle_serial_monitor(self, checked: bool) -> None:
        if checked:
            self.current_com_port = self.detect_com_port()
            if not self.current_com_port:
                self.txt_monitor.append("<span style='color:red;'>[Error]: Board not found!</span>")
                self.btn_monitor.setChecked(False)
                 return
            try:
                if CURRENT_TOOL_DIR not in sys.path: 
                    sys.path.insert(0, CURRENT_TOOL_DIR)
                 import serial
                active_baud: int = self.BAUD_RATES[self.current_baud_index]
                self.serial_port = serial.Serial(
                    port=self.current_com_port, baudrate=active_baud,
                    parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS, timeout=0.01 
                )
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                self.serial_port.dtr = True
                self.serial_port.rts = True
                time.sleep(0.06)
                self.serial_port.dtr = False
                
                if hasattr(self, 'plotter_widget') and self.plotter_widget:
                     self.plotter_widget.start_time = time.perf_counter()
                
                self.txt_monitor.clear()
                self.txt_monitor.append(f"<span style='color:yellow;'>[Moni torus]: Connected to {self.current_com_port} ({active_baud} baud).</span><br>")
                 self.btn_monitor.setText("Close")
                
                if self.serial_timer is None:
                    self.serial_timer = QtCore.QTimer(self)
                    self.serial_timer.timeout.connect(self.read_serial_buffer)
                    self.serial_timer.start(16) 
            except Exception as e:
                self.txt_monitor.append(f"<span style='color:red;'>[Port Error]: {str(e)}</span>")
                self.stop_monitor_internally()
        else:
            self.stop_monitor_internally()

    def read_serial_buffer(self) -> None:
        if hasattr(self, 'serial_port') and self.serial_port and getattr(self.serial_port, 'is_open', False):
            try:
                if self.serial_port.in_waiting > 0:
                    data: bytes = self.serial_port.read(self.serial_port.in_waiting)
                    raw_text: str = data.decode('utf-8', errors='ignore')
                    if raw_text:
                        is_graph_mode: bool = self.btn_mode_toggle.isChecked()
                        if not is_graph_mode:
                            self.txt_monitor.blockSignals(True)
                            cursor = self.txt_monitor.textCursor()
                            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
                            cursor.insertText(raw_text)
                            self.txt_monitor.setTextCursor(cursor)
                            self.txt_monitor.ensureCursorVisible()
                            self.txt_monitor.blockSignals(False)
                        
                         if len(self.txt_monitor.toPlainText()) > 3000:
                            self.txt_monitor.clear()
                            self.txt_monitor.append( "<span style='color:gray;'>[Log cleared]</span><br>")
                        
                        for line in raw_text.split('\n'):
                            clean_line: str = line.strip()
                            if clean_line:
                                      try:
                                     float_val: float = float(clean_line)
                                    se lf.plotter_widget.add_value(float_val)
                                     except ValueError:
                                    pass 
            except Exception as e:
                self.txt_monitor.blockSignals(False)
                self.txt_monitor.append(f"<span style='color:red;'>[Critical buffer error]: {str(e)}</span>")
                self.stop_monitor_internally()

    def stop_monitor_internally(self) -> None:
        if self.serial_timer is not None:
            self.serial_timer.stop()
            self.serial_timer.deleteLater()
            self.serial_timer = None
        if hasattr(self, 'serial_port') and self.serial_port:
            try:
                if getattr(self.serial_port, 'is_open', False):
                    self.serial_port.cancel_read()
                    self.serial_port.cancel_write()
                    self.serial_port.close()
            except Exception as e:
                print(f"[Error closing port]: {e}", file=sys.stderr)
        self.serial_port = None
        self.txt_monitor.clear()
        if hasattr(self, 'plotter_widget') and self.plotter_widget:
            self.plotter_widget.clear_graph() # Restored call clear graph
         self.btn_monitor.setChecked(False)
        self.btn_monitor.setText("Monitor")
        self.sync_hardware_settings()
        
# ==============================================================================
#  OFFICIAL OPEN CONTRACT SYNCHRONIZATION STEM CONTEXT API v1.0 SPECIFICATION
# ==============================================================================
#  This manifest describes the structure of raw system data, which is main
#  engineering remote provides upon request to any external AI modules or plugins.
#
#  FORMAT SYNCHRONOUS RESPONSE METHOD get_current_stem_context() -> dict:
#  {
#      "environment": "String",  # Active engineering development environment.
#                                # Options: "ard uino", "freecad", "trik", "pico", "pi", "unknown"
#
#      "board": "String",        # Human-readable name of the selected hardware board.
#                                # Applicable  for "arduino". If the environment is different — "unknown"
#
#      "port": "String"          # Identifier of the active COM port (e.g. "COM4").
" arduino" and "trik". If not found — "Not connected"
#  }
# ==============================================================================

    def get_current_stem_context(self) -> dict:
        context = {"environment": "unknown", "board": "unknown", "port": "unknown"}
        sh = pyzo.shells.getCurrentShell()
        if not sh:
             return context
            
        shell_name = str(sh._info.name if hasattr(sh, '_info') else sh.name).lower().strip()
        
        # Definition of the current engineering environment
        if "arduino" in shell_name:
            context["environment"] = "arduino"
             context["board"] = self.combo_boards.currentText()
            context["port"] = self.current_com_port if self.current_com_port else "Not connected"
        elif "freecad" in shell_name:
            context["environment"] = "freecad"
        elif "trick" in shell_name or "trik" in shell_name:
            context["environment"] = "trik"
        elif "pico" in shell_name or "micropython" in shell_name:
            context["environment"] = "pico"
        elif "pi" in shell_name:
            context["environment"] = "pi"
            
        return context

    def show_stem_educational_tip(self) -> None:
        ed = pyzo.editors.getCurrentEditor()
        if not ed: 
            return
            
        code_edit_widget = ed._codeEdit if hasattr(ed, '_codeEdit') else ed
        if not hasattr(code_edit_widget, 'textCursor'): 
            return
            
        # Reading an atomic word from the editor strictly under the text cursor
        cursor = code_edit_widget.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        token_raw = cursor.selectedText().strip()
        if not token_raw: 
            return
            
        # Assembly of composite prefixes (bridge to class methods)
        try:
            full_line = cursor.block().text()
            pos_in_line = cursor.selectionStart() - cursor.block().position()
            left_part = full_line[max(0, pos_in_line - 15):pos_in_line].strip()
            
            for prefix in ["gpio.", "machine.", "doc.", "br ick.", "app.", "gui.", "Serial.", "GPIO.", "App.", "Gui."]:
                if left_part.endswith(prefix) or left_part.lower().endswith(prefix.lower()):
                    token_raw = prefix + token_raw
                     break
        except Exception:
            pass
            
        token_lower = token_raw.lower()
        sh = pyzo.shells.getCurrentShell()
        if not sh: 
            return
            
        # Initialize data sub structure containers
        keywords_db = {}
        errors_db = {}
        
        # Reading local JSON cache from disk
        if hasattr(ed, '_universal_stem_filter') and ed._universal_stem_filter:
            cache_data = ed._universal_stem_filter.read_cached_keywords()
            keywords_db = cache_data.get("keywords", {})
            errors_db = cache_data.get("errors", {})
            
        # FOLBECK-INSURANCE: If the disk is busy, look at the live RAM of Shell
        if not keywords_db and hasattr(sh, 'get_env'):
            try:
                env = sh.get_env()
                if "__STEM_API__" in env and isinstance(env["__STEM_API__"], dict):
                    keywords_db = env["__STEM_API__"].get("keywords", {})
                    errors_db = env["__STEM_API__"].get("errors", {})
              except Exception:
                 pass
                
        if not keywords_db: 
             return
            
        # Atomic token segment parsing
        pure_token = token_raw.split('.')[-1]
        pure_lower = pure_token.lower()
        
        # Building a register map for autocorrect
        exact_case_map = {k.lower(): k for k in keywords_db.keys()}
        exact_word = exact_case_map.get(pure_lower, pure_token)
        
        # Match Check. The word is considered correct, 
        # if either the complete string (with prefix), or its final part is in the database with exact case!
        is_perfect_match = (token_raw in keywords_db) or (pure_token in keywords_db) or (token_raw == "print")
        error_desc = ""
        
        # If the register is violated (the word is really not in the database in such register, but it is in principle)
        if not is_perfect_match and pure_lower in exact_case_map:
            error_desc = errors_db.get(token_lower) or errors_db.get(pure_lower, "")
            if not error_desc:
                error_desc = f"Case letter error! Correct spelling of command: {exact_word}"
                
        if token_raw == "Print" and not error_desc:
            error_desc = "Caps of built-in functions! In Python commands are written with lowercase letters. Correct: print(...)"
            
        # Finding a text area in Shell for output a card
        shell_edit = None
        if hasattr(sh, '_codeEdit'): 
            shell_edit = sh._codeEdit
        elif hasattr(sh, 'toPlainText'): 
            shell_edit = sh
        if not shell_edit: 
            return
            
         # ==============================================================================
        # FORMING HTML OUTPUT IN THE COMMENT AREA SHELL
        # ==============================================================================
        if error_desc:
            html_card = (
                f"<div style='border: 2px solid #d32f2f; padding:  8px; background-color: #fdf2f2; margin: 4px; border-radius: 4px;'>"
                f"  <b style='color: #c62828; font-size: 11px; '> [SYSTEM STEM ATTENTION]: ERROR DETECTED IN TEXT</b><br>"
                f"  <p style='color: #b71c1c; margin-top : 6px; margin-bottom: 2px; font-family: Consolas; font-s ize: 10px; background-color: #f5f5f5; padding: 4px; border: 1px solid #e0e0e0;'>Error in token: {token_raw}</p>"
                f"  <p style='color: #e65100; margin-top: 6px ; font-size: 10px; font-weight: bold;'>System hint:</p>"
                f"  <p style='color: #212121; margin-top:  2px; font-size: 10px; line-height: 14px;'>{error_desc}</p>"
                f"</div><br><b>>>> </b>"
            )
            self._write_html_to_shell(shell_edit, html_card)
            return
            
        else:
            help_block = keywords_db.get(token_raw) or keywords_db.get(exact_word) or keywords_db.get(pure_lower)
            if not help_block: 
                 return
                
            title = help_block.get("title", token_raw)
            desc = help_block.get("desc", "Instructions STEM")
            syntax = help_block.get("syntax", "")
            warn = help_block.get("warn", "")
            
            html_card = (
                f"<div style='border: 2px solid #2e7d32; padding:  8px; background-color: #edf7ed; margin: 4px; border-radius: 4px;'>"
                f"  <b style='color: #1b5e20; fo nt-size: 11px;'> [HELP STEM]: {title}</b><br>"
                f"  <p style='color: #333333; margin-to p: 6px; font-size: 10px; line-height: 14px;'>{desc}</p>"
            )
             if syntax:
                html_card += f"  <p style='color: #0d47a1; margin-top: 4px ; font-family: Consolas; font-size: 10px;'><b>Syntax:</b> {syntax}</p>"
            if warn:
                html_card += f"  <p style='color: #b71c1c; margi n-top: 4px; font-size: 10px;'> <b>Warning:</b> {warn}</p>"
            html_card += "</div><br><b>>>> </b>"
            
            self._write_html_to_shell(shell_edit, html_card)

    def _write_html_to_shell(self, shell_edit: Any, html_content: str) -> None:
        """Thread-safely updates a Shell text field, preventing Qt signal looping."""
        try:
            shell_edit.blockSignals(True)
            shell_edit.clear()
            sh_cursor = shell_edit.textCursor()
            sh_cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            sh_cursor.insertHtml(html_content)
            shell_edit.setTextCursor(sh_cursor)
        finally:
            shell_edit.blockSignals(False)

    def run_remote_ssh_code(self) -> None:
        """A remote method that calls remote running a script via SSH in the Pyzo console."""
        ed = pyzo.editors.getCurrentEditor()
        if ed and hasattr(ed, 'filename') and ed.filename:
            try:
                ed.save()
                filename_base = os.path.basename(ed.filename)
                
                # Reading dynamic authorization parameters from the remote panel
                current_ip = self.txt_ip.text().strip()
                if not current_ip:
                      current_ip = "192.168.1.100"
                    
                 current_password = self.txt_password.text().strip()
                if not current_password:
                    current_password = "raspberry"
                    
                sh = pyzo.shells.getCurrentShell()
                if sh:
                    # Passing file name, target IP and password to runtime function
                    sh.executeCommand(f"run_pi('{filename_base}', '{current_ip}', '{current_password}')")
            except OSError as e:
                print(f"[Remote SSH Error]: Failed to save file: {e}", file=sys.stderr)

    def close(self) -> None:
        self.stop_monitor_internally()
        super().close()
        
import zipfile
import shutil

class ArduinoLibraryManagerDialog(QtWidgets.QDialog):
    """Graphical offline Arduino library manager."""
    def __init__(self, cli_path: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.CLI_PATH: str = cli_path
        self.setWindowTitle("Arduino STEM Library Manager (Standalone Offline Engine)")
        self.setMinimumSize(650, 480)
        self.setStyleSheet("background-color: #252526; color: #ffffff;")
        
        # Local Match Database "Name -> Data JSON Structure"
        self.local_db_map: Dict[str, Dict[str, Any]] = {}
        
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)
        
         # --- BLOCK 1: Local search by saved index ---
        self.search_group = QtWidgets.QGroupBox("Search and install from local repository database")
        self.search_group.setStyleSheet("color: #00e5ff; font-weight: bold;")
        self.search_layout = QtWidgets.QVBoxLayout(self.search_group)
        
        self.input_layout = QtWidgets.QHBoxLayout()
        self.txt_search = QtWidgets.QLineEdit()
        self.txt_search.setPlaceholderText("Initializing local index...")
        self.txt_search.setStyleSheet("background-color: #1e1e1e; color: #ffffff; border: 1px solid #3c3c3c; padding: 4px;")
        self.txt_search.returnPressed.connect(self.perform_local_search)
        self.input_layout.addWidget(self.txt_search)
        
        self.btn_search = QtWidgets.QPushButton("Find locally")
        self.btn_search.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 4px 12px;")
        self.btn_search.clicked.connect(self.perform_local_search)
        self.input_layout.addWidget(self.btn_search)
        self.search_layout.addLayout(self.input_layout)
        
        # List of offline search results
        self.list_results = QtWidgets.QListView()
        self.list_results.setStyleSheet("background-color: #1e1e1e; color: #ffffff; border: 1px solid #3c3c3c;")
        self.results_model = QtCore.QStringListModel([], self.list_results)
        self.list_results.setModel(self.results_model)
        self.search_layout.addWidget(self.list_results)
        
        self.btn_install_selected = QtWidgets.QPushButton("Unpack and install selected library")
        self.btn_install_selected.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        self.btn_install_selected.clicked.connect(self.install_local_cached_library)
        self.search_layout.addWidget(self.btn_install_selected)
        self._layout.addWidget(self.search_group)
        # --- BLOCK 2: Import arbitrary .ZIP folders ---
        self.zip_group = QtWidgets.QGroupBox("Manual import external archives")
         self.zip_group.setStyleSheet("color: #ff9100; font-weight: bold;")
        self.zip_layout = QtWidgets.QHBoxLayout(self.zip_group)
        
        self.btn_import_zip = QtWidgets.QPushButton("Connect library from an arbitrary .ZIP archive...")
        self.btn_import_zip.setStyleSheet("background-color: #ff9100; color: #1e1e1e; font-weight: bold; padding: 8px;")
        self.btn_import_zip.clicked.connect(self.import_zip_library)
        self.zip_layout.addWidget(self.btn_import_zip)
        self._layout.addWidget(self.zip_group)
        
        # --- BLOCK 3: Output Console (Logger) ---
        self.txt_log = QtWidgets.QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(95)
        self.txt_log.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 10px;")
        self._layout.addWidget(self.txt_log)
        
        # Loading the database from disk using Python at startup
        self.load_local_json_index()

    def load_local_json_index(self) -> None:
        """Reads saved library_index.json from disk and builds search hash-map."""
        import json
        appdata: str = os.environ.get('APPDATA', '')
        json_path = os.path.join(appdata, 'pyzo', 'tools', 'Arduino', 'staging', 'registry.arduino.cc', 'library_index.json')
        
        if not os.path.exists(json_path):
            self.txt_log.append(f"<span style='color:orange;'>[Offline]: Index file not found at path: {json_path}</span>")
            self.txt_log.append("[Status]: Connected emergency manual ZIP-import.")
            self.txt_search.setPlaceholderText("Local index on disk is empty.")
            return
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                 raw_data = json.load(f)
                
            libs_list = raw_data.get('libraries', [])
            self.local_db_map.clear()
            
            for lib in libs_list:
                name = lib.get('name', '')
                version = lib.get('version', '')
                sentence = lib.get('sentence', 'Offline STEM module')
                 if name:
                    display_title = f"{name} [v{version}] - {sentence}"
                    self.local_db_map[display_title] = lib
                    
            self.txt_log.append(f"<span style='color:#00ff00;'>[Status]: STANNEL DATABASE CONNECTED. Available offline modules: {len(self.local_db_map)}</span>")
            self.txt_search.setPlaceholderText("Enter keyword (for example: Servo, DHT)...")
        except Exception as e:
            self.txt_log.append(f"<span style='color:red;'>[JSON Parser Failure]: {e}</span>")

    def perform_local_search(self) -> None:
        """Search by local hash map."""
        query: str = self.txt_search.text().strip().lower()
        if not query:
            self.txt_log.append("<span style='color:yellow;'>[Attention]: Enter a search query!</span>")
            return
            
        filtered_results: List[str] = []
        for display_title in self.local_db_map.keys():
            if query in display_title.lower():
                filtered_results.append(display_title)
                
        self.results_model.setStringList(sorted(filtered_results))
        self.txt_log.append(f"<span style='color:green;'>[Success]: Found in local index: {len(filtered_results)}</span>")

     def install_local_cached_library(self) -> None:
        """Gives the CLI command to install a library from the local staging folder."""
        index: QtCore.QModelIndex = self.list_results.currentIndex()
        if not index.isValid():
            self.txt_log.append("<span style='color:yellow;'>[Attention]: Select a library from search results!</span>")
            return
            
        display_name: str = index.data()
        lib_data = self.local_db_map.get(display_name, {})
        lib_name = lib_data.get('name', '')
        archive_name = lib_data.get('archiveFileName', '')
        
        if not lib_name or not archive_name: return
        
        appdata: str = os.environ.get('APPDATA', '')
        src_zip_path = os.path.join(appdata, 'pyzo', 'tools', 'Arduino', 'staging', 'registry.arduino.cc', archive_name)
        
        if not os.path.exists(src_zip_path):
            self.txt_log.append(f"<span style='color:#ff5252;'>[Error]: F archive ile '{archive_name}' is physically absent in the staging folder!</span>")
            return

        self.txt_log.append(f"[Offline Install]: Extract and integrate module '{lib_name}'...")
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        
        local_arduino_dir: str = os.path.join(appdata, 'pyzo', 'tools', 'Arduino')
        
        custom_env = os.environ.copy()
        custom_env["ARDUINO_LIBRARY_ENABLE_UNSAFE_INSTALL"] = "true"
        
        # Calling the original installation CLI
        cmd: str = f'chcp 65001 > nul && "{self.CLI_PATH}" config set directories. data "{local_arduino_dir}" && "{self.CLI_PATH}" lib install "{lib_name}" --offline'
        try:
             result = subprocess.run(cmd, shell=True, capture_output=True, env=custom_env)
            if result.returncode == 0:
                self.txt_log.append(f"<span style='color:green; '>[SUCCESS]: Library '{lib_name}' successfully installed!</span>")
                QtWidgets.QMessageBox.information(self, "Offline installation completed", f"Library '{lib_name}' successfully connected.")
            else:
                raw_error = result.stderr if result.stderr else result.stdout
                error_text = raw_error.decode('utf-8', errors='ignore').strip() if raw_error else "Cache error"
                if "Current code page" in error_text:
                    error_text = error_text.split("\n")[-1].strip()
                self.txt_log.append(f"<span style='color:#ff5252;'>[CLI Error]: {error_text}</span>")
        except subprocess.SubprocessError as e:
            self.txt_log.append(f"<span style='color:#ff5252;'>[Critical subprocess failure]: {e}</span>")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def import_zip_library(self) -> None:
        """Import .ZIP file via Arduino CLI."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select at ZIP archive Arduino library", "", "Arduino Library Archive (*.zip)")
        if not file_path: return
        
        self.txt_log.append(f"[Import]: Unpacking and installing local archive '{os.path.basename(file_path)}'...")
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        
        custom_env = os.environ.copy()
        custom_env["ARDUINO_LIBRARY_ENABLE_UNSAFE_INSTALL"] = "true"
        
        # Call arduino-cli lib install --zip-path
        cmd: str = f'chcp 65001 > nul && "{self.CLI_PATH}" lib install --zip-path "{file_path}"'
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, env=custom_env)
            if result.returncode == 0:
                 self.txt_log.append("<span style='color:green;'>[Success]: Module from ZIP-folder successfully connected to the learning environment!</span>")
                QtWidgets.QMessageBox.information(self, "Import for complete", "The library successfully added and is ready for use.")
            else:
                raw_error = result.stderr if result.stderr else result.stdout
                error_text = raw_error.decode('utf-8', errors='ignore').strip() if raw_error else "Unpacking error"
                if "Current code page" in error_text:
                    error_text = error_text.split("\n")[-1].strip()
                self.txt_log.append(f"<span style='color:red;'>[CLI Error]: {error_text}</span>")
        except subprocess.SubprocessError as e:
            self.txt_log.append(f"<span style='color:red;'>[Critical import failure]: {e}</span>")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
