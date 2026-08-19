import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import re
import atexit
import socket
from typing import List ,  Dict ,  Set, Optional, Any
from pyzo. qt import QtCore ,  QtGui ,  QtWidgets
import pyzo
from pyzo import translate

#  Global   name   of the   plugin   for   registration   in   the   Environment   menu
tool_name  = translate(" AIAssistantTool ", " AI Assistant tool ")

def ensure_portable_ollama_running () -> None:
    """ Checks   the status   of   Ollama .  If   the   server   is sleeping ,   secretly   wakes   it   from   the   STEM   folder ."""
    try:
        with urllib.request.urlopen("http://localhost:11434/", timeout=1) as r:
             if r.getcode () == 200:
                return  # Active
     except Exception :
        pass
    
    current_tool_dir = os.path.dirname(os.path.abspath(__file__))
    stem_root_dir = os.path.abspath(os.path.join(current_tool_dir, '..', '..', '..', '..'))
     base_dir  =  os.path.join (stem_root_ dir , " Ollama ")
     ollama_exe  =  os.path.join (base_ dir , "servers", "ollama.exe")
     config_dir  =  os.path.join (base_ dir , " servers", "config ")
     models_dir  =  os.path.join (base_ dir , "models")
    
     if not os.path.exists ( ollama_exe ):
         print(f"[AI Assistant tool]: File not found: {ollama_exe}", file=sys.stderr, flush=True)
        return
        
    env =  os.environ.copy ()
    env["OLLAMA_MODELS"] =  models_dir
    env["LOCALAPPDATA"] =  os.path.join (config_ dir , "local")
    env["APPDATA"] =  os.path.join (config_ dir , "roaming")
    env["USERPROFILE"] =  config_dir
    env["OLLAMA_NUM_PARALLEL"] = "1"
    
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
         subprocess.Popen (
            [ ollama_exe, "serve "],
            env=env,
             creationflags = creationflags ,
             stdout = subprocess.DEVNULL ,
            stderr= subprocess.DEVNULL
        )
     except Exception as e :
        print(f"[AI Assistant tool]: Server autostart failed: {e}", file=sys.stderr, flush=True)

def kill_ollama_process_tree ():
    """ Force   cleans   the   process   tree   of Ollama   when   closing   Pyzo ."""
    try:
         if sys.platform  == "win32":
            subprocess.Popen(["taskkill", "/f", "/t", "/im", "ollama.exe"], creationfl ags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.Popen(["taskkill", "/f", "/t", "/im", "llama-server.exe"], creatio nflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["pkill", "-f", "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.Popen(["pkill", "-f", "llama-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
     except Exception :
         pass
class OllamaWorker ( QtCore.QThread ):
    """ Background   worker   thread   AI   with   protection   from   timeouts   sockets ."""
     signal_chunk  =  QtCore.Signal (str)       
     signal_finished  =  QtCore.Signal (str)    
     signal_error  =  QtCore.Signal (str)       
    
    def __init__(self, action_type: str, code_text: str, context_info: dict, user_question: str = "") -> None:
        super().__ init __()
         self.action_type  =  action_type
         self.code_text  =  code_text
         self.context_info  =  context_info
         self.user_question  =  user_question
         self.api_url  = "http://localhost:11434/ api /generate"
        self._ is_cancelled  = False
        
     def cancel (self) -> None:
        self._ is_cancelled  = True
        
     def run (self) -> None:
         if self ._ is_cancelled :
            return
            
         system_prompt  = (
           " You are  —  patient ,   concise   and   highly qualified   teacher   of engineering   programming   and   robotics   at   school . "
           " Your   goal   is   to help   the student   understand   his   code   and   find   hidden   vulnerabilities ,  not   write   a   solution   for   him . "
           " Answer   strictly   in   Russian   language ,   friendly ,   structured   and   concisely   ( no more   than   4-5   sentences ).\n"
           " CRITICAL   RULES   FOR CONDUCTING   DIALOGUE   FOR   ALL   ENVIRONMENTS :\n"
            "1.  Never   assert   errors   with   100 %   certainty ,   unless   it   is   an obvious   syntactic   failure .  "
           " Instead of   the phrases  ' sorry   for   the error '  or  ' this   will   lead   to   the error '  ALWAYS   use   the constructions : "
           "' I suspect   an error ...', ' Perhaps   here   it is worth   checking ...', ' It seems   in   this   line ...'.\n"
            "2.  Never   make up non - existent   errors   ( for example ,   false   statements   about   incorrect   ports   pins   or   names   of built-in   functions ) .\n"
            "3.  Focus   on   logic :   briefly   describe   what   the code   does ,   and   gently   point out   to the student   what   to pay   attention to ."
        )
        
        env_type = self.context_info.get("environment", "unknown")
         if env_type  == " arduino ":
           system_prompt += f"\nCurrently the student is working in the Arduino C++ environment.  Selected   board : { self.context_info.get (' board', 'Uno ')}.  Give   advice   taking into account   the   syntax   of   C   and   electronics ."
         elif env_type  == " freecad ":
             system_prompt  += "\n Currently   the student   is designing   a   3D model   in   FreeCAD   in   Python.  Consider   the features   of   FreeCAD API   and   topology ."
         elif env_type in  [" pico ", "pi", " trik "]:
             system_prompt  += f"\n Currently   the student   is working   with   a hardware   robot   in   the  { env_type.upper ()}  environment in  Python."
             if env_type  == " trik ":
                 system_prompt  += (
                   "\n IMPORTANT   RULE   FOR   TRICKS :  The   robot   has   TWO   leading   motors :  left   'M1'  and   right   'M2'. "
                   " To   drive   forward   in   a straight line ,  you   must   ALWAYS   turn on   both   motors   with   the same   power : "
                    "brick.motor('M1').setPower(100) and brick.motor('M2').setPower(100). "
                   " To   move   a given   distance   or   time   use   a time delay ,   for example : "
                   " import time ;  time.sleep (2) ( drive  2  seconds ),  and   then   be sure   to stop   the motors   through  .brake()."
                )
            
         if self.action_type  == "explain":
             user_prompt  = f" Explain   in simple   words   how   this   code fragment   works :\n```\n{ self.code_text }\n```"
         elif self.action_type  == "comments":
            user_prompt = f"Add neat comments to this code:\n```\n{self.code_text}\n```"
         elif self.action_type  == " logic_errors ":
            user_prompt = f"Check this code fragment for hidden logical errors:\n```\n{self.code_text}\n```"
         elif self.action_type  == "optimize":
            user_prompt = f"Optimize this code fragment, make it cleaner:\n```\n{self.code_text}\n```"
         elif self.action_type  == "chat":
             user_prompt = f"Code Context:\n```\n{self.code_text}\n```\nQuestion: {self.user_question}"
        else:
             user_prompt  =  self.user_question
            
        payload = {
            "model": "qwen2.5-coder:1.5b", 
            "prompt":  user_prompt ,
            "system":  system_prompt ,
            "stream": True,
            " keep_alive ": "5m",
            "options": {
                "temperature": 0.2,
                " num_ctx ": 2048
            }
        }
        
        try:
             socket.setdefaulttimeout (300)
            req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req, timeout=300) as response:
                 local_buffer  = []
                 for line in response :
                     if self ._ is_cancelled :
                           return
                     if not line.strip ():
                          continue
                     try:
                        parsed_line = json.loads(line.decode('utf-8'))
                        chunk =  parsed_line.get ("response", "")
                          if chunk :
local_buffer.append (chunk )
self.signal_chunk.emit (str(chunk) )
QtCore.QThread.msleep (15 )
                         if parsed_line.get (" done", False ):
                             break
                     except json.JSONDecodeError :
                         break
                        
                 self.signal_finished.emit ("".join( local_buffer ))
         except urllib.error.URLError as e :
            self.signal_error.emit(f"Failed to contact Ollama API.\nEnsure that the qwen2.5-coder:1.5b model has been successfully loaded.\n({str(e)})")
         except Exception as e :
            self.signal_error.emit(f"An unexpected generation error occurred: {str(e)}")
class AIAssistantPanel ( QtWidgets.QWidget ):
    """ Graphic   panel   AI - Assistant   with   native   support   Qt   6.8.1."""
     def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__ init __(parent)
         self._worker : Optional[ OllamaWorker ] = None
         self.init_ui ()
        
     def init_ui (self) -> None:
         self.main_layout  =  QtWidgets.QVBoxLayout (self)
         self.main_layout.setContentsMargins (2, 2, 2, 2)
         self.main_layout.setSpacing (4)
        
         self.buttons_widget  =  QtWidgets.QWidget ()
        self.buttons_layout = QtWidgets.QHBoxLayout(self.buttons_widget)
         self.buttons_layout.setContentsMargins (0, 0, 0, 0)
         self.buttons_layout.setSpacing (4)
        
        self.btn_explain = QtWidgets.QPushButton("Explain highlighted code")
        self.btn_comments = QtWidgets.QPushButton("Add comments (#)")
        self.btn_errors = QtWidgets.QPushButton("Check for logical errors")
        self.btn_optimize = QtWidgets.QPushButton("Optimize")
        
         self.btn_chat_toggle  =  QtWidgets.QPushButton ("   Chat ")
         self.btn_chat_toggle.setCheckable (True)
        self.btn_chat_toggle.setStyleSheet("font-weight: bold; background-color: #3a3a3a;")
        
        self.btn_explain.clicked.connect(lambda: self.handle_ai_action("explain"))
        self.btn_comments.clicked.connect(lambda: self.handle_ai_action("comments"))
        self.btn_errors.clicked.connect(lambda: self.handle_ai_action("logic_errors"))
        self.btn_optimize.clicked.connect(lambda: self.handle_ai_action("optimize"))
        self.btn_chat_toggle.clicked.connect(self.toggle_panel_state)
        
         self.buttons_layout.addWidget ( self.btn_explain )
         self.buttons_layout.addWidget ( self.btn_comments )
         self.buttons_layout.addWidget ( self.btn_errors )
         self.buttons_layout.addWidget ( self.btn_optimize )
         self.buttons_layout.addWidget ( self.btn_chat_toggle )
         self.buttons_layout.addStretch (1)
        
         self.main_layout.addWidget ( self.buttons_widget )
        
         self.chat_area_widget  =  QtWidgets.QWidget ()
        self.chat_area_layout = QtWidgets.QVBoxLayout(self.chat_area_widget)
         self.chat_area_layout.setContentsMargins (0, 2, 0, 0)
         self.chat_area_layout.setSpacing (4)
        
         self.txt_chat_history  =  QtWidgets.QTextBrowser ()
         self.txt_chat_history.setReadOnly (True)
        self.txt_chat_history.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', monospace; font-size: 11px;")
        
         self.chat_input_widget  =  QtWidgets.QWidget ()
        self.chat_input_layout = QtWidgets.QHBoxLayout(self.chat_input_widget)
         self.chat_input_layout.setContentsMargins (0, 0, 0, 0)
         self.chat_input_layout.setSpacing (4)
        
         self.input_field  =  QtWidgets.QLineEdit ()
        self.input_field.setPlaceholderText("Ask a a AI engineer question here...")
        self.input_field.returnPressed.connect(self.send_chat_message)
        
         self.btn_send  =  QtWidgets.QPushButton (" Send ")
         self.btn_send.clicked.connect ( self.send_chat_message )
        
         self.chat_input_layout.addWidget ( self.input_field )
         self.chat_input_layout.addWidget ( self.btn_send )
        
        self.chat_area_layout.addWidget(self.txt_chat_history, 1)
         self.chat_area_layout.addWidget ( self.chat_input_widget )
        
         self.main_layout.addWidget ( self.chat_area_widget )
        
         self.global_spacer  =  self.main_layout.addStretch (1)
         self.chat_area_widget.hide ()

     def toggle_panel_state (self) -> None:
         " "" Thread-safe   resizing   dock   via   native   resizeDocks   method for   Qt   6 . """
        dock = self.parentWidget().parent() if hasattr(self.parentWidget(), 'parent') else None
        if not dock or not isinstance(dock, QtWidgets.QDockWidget):
            return
            
         if self.btn_chat_toggle.isChecked ():
             self.chat_area_widget.show ()
            #  Universal   method  Qt 6  for   opening   the   bottom   panel   up
            pyzo.main.resizeDocks([dock], [220], QtCore.Qt.Orientation.Vertical)
        else:
             self.chat_area_widget.hide ()
            #  Universal   method  Qt 6  for   collapsing   the   bottom   panel   into   a thin   strip
            pyzo.main.resizeDocks([dock], [38], QtCore.Qt.Orientation.Vertical)
            
    def _ stop_existing_worker (self) -> None:
         if self ._ worker and self ._ worker.isRunning ():
            self._ worker.cancel ()
            self._ worker.quit ()
            self._ worker.wait ()
            
     def handle_ai_action (self,  action_type : str) -> None:
         context_info  = {"environment": "unknown"}
        tool =  pyzo.toolManager.getTool (" EngineeringPanelTool ") 
         if tool and hasattr (tool, ' get_current_stem_context '):
             context_info  =  tool.get_current_stem_context ()
            
         selected_code  = ""
        ed =  pyzo.editors.getCurrentEditor ()
         if ed :
            code_edit_widget = ed._codeEdit if hasattr(ed, '_codeEdit') else ed
             if hasattr (code_edit_widget, ' textCursor '):
                cursor =  code_edit_widget.textCursor ()
                 if cursor.hasSelection ():
                     selected_code  =  cursor.selectedText ()
                    
         if not selected_code.strip ()  and action_type  != "chat":
            QtWidgets.QMessageBox.warning(self, "Context not found", "Please select some code before pressing the button!")
            return
            
         self.chat_area_widget.show ()
         self.btn_chat_toggle.setChecked (True)
         self.txt_chat_history.clear ()
         self.txt_chat_history.append ("--- Request sent to local model Qwen 2.5-Coder (1.5B) ---")
        
         self.set_buttons_enabled (False)
        self._ stop_existing_worker ()
        self._worker = OllamaWorker(action_type, selected_code, context_info)
        self._worker.signal_chunk.connect(self.on_ai_chunk_received)
         self._worker.signal_finished.connect(self.on_ai_generation_finished)
        self._worker.signal_error.connect(self.on_ai_error_occurred)
        self._ worker.start ()
     def send_chat_message (self) -> None:
        question =  self.input_field.text ().strip()
         if not question :
            return
            
         self.input_field.clear ()
        self.txt_chat_history.append(f"\nYou: {question}\nAI Assistant: ")
        
         context_info  = {"environment": "unknown"}
        tool =  pyzo.toolManager.getTool (" EngineeringPanelTool ")
         if tool and hasattr (tool, ' get_current_stem_context '):
             context_info  =  tool.get_current_stem_context ()
            
         selected_code  = ""
        ed =  pyzo.editors.getCurrentEditor ()
         if ed :
            code_edit_widget = ed._codeEdit if hasattr(ed, '_codeEdit') else ed
             if hasattr (code_edit_widget, ' textCursor '):
                cursor =  code_edit_widget.textCursor ()
                 if cursor.hasSelection ():
                     selected_code  =  cursor.selectedText ()
                    
         self.set_buttons_enabled (False)
        self._ stop_existing_worker ()
        self._worker = OllamaWorker("chat", selected_code, context_info, user_question=question)
        self._worker.signal_chunk.connect(self.on_ai_chunk_received)
        self._worker.signal_finished.connect(self.on_ai_generation_finished)
        self._worker.signal_error.connect(self.on_ai_error_occurred)
        self._ worker.start ()
        
     def on_ai_chunk_received (self,  text_chunk : str) -> None:
         if not text_chunk :
            return
        if "```python"  in text_chunk :
            text_chunk = text_chunk.replace("```python", "```python\n")
            
        try:
            self.txt_chat_history.moveCursor(QtGui.QTextCursor.MoveOperation.End)
             self.txt_chat_history.insertPlainText ( text_chunk )
             self.txt_chat_history.ensureCursorVisible ()
         except Exception :
            pass
        
     def on_ai_generation_finished (self,  full_text : str) -> None:
        self.txt_chat_history.moveCursor(QtGui.QTextCursor.MoveOperation.End)
         self.txt_chat_history.insertPlainText ("\n\n--------------------------------------------------\n")
         self.txt_chat_history.ensureCursorVisible ()
         self.set_buttons_enabled (True)
         self._worker  = None
        
     def on_ai_error_occurred (self,  error_message : str) -> None:
        self.txt_chat_history.append(f"\n[ERROR]: {error_message}\n")
         self.set_buttons_enabled (True)
         self._worker  = None
        
     def set_buttons_enabled ( self, enabled : bool) -> None:
         self.btn_explain.setEnabled (enabled)
         self.btn_comments.setEnabled (enabled)
         self.btn_errors.setEnabled (enabled)
         self.btn_optimize.setEnabled (enabled)
         self.btn_send.setEnabled (enabled)
         self.input_field.setEnabled (enabled)

class AIAssistantTool ( QtWidgets.QWidget ):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
         super().__ init __(parent)
         self.setWindowTitle ( tool_name )
        
        self._ main_layout  =  QtWidgets.QVBoxLayout (self)
        self._ main_layout.setContentsMargins (0, 0, 0, 0)
         self.setLayout (self._ main_layout )
        
         self.ai_panel  =  AIAssistantPanel (self)
        self._ main_layout.addWidget ( self.ai_panel )
        
        #  Postpone   execution   of   native   relocation   until   complete   initialization   of   the   Pyzo   interface
         QtCore.QTimer.singleShot (0, self._fix_docking_location)
        
    def  _fix_docking_location (self) -> None:
        """ Redistribution of   dock areas   main   window   ( Native   specification   Pyzo   for   Qt   6)"" "
        try:
            dock =  self.parent ()
             if isinstance (dock,  pyzo.tools.ToolDockWidget ):
                #  Universal   method   for   obtaining   an area   ( works   on  Qt 6.8.1)
                 current_area  =  pyzo.main.dockWidgetArea (dock)
                if current_area == QtCore.Qt.DockWidgetArea.RightDockWidgetArea:
                    pyzo.main.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
                    pyzo.main.setCorner(QtCore.Qt.Corner.Bot tomRightCorner, QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
                    
                    #  FOR  QT 6.8.1:  Instead of   dock.resize   use   global   window   layout   manager .
                    #  Collapse   the dock   exactly   to   the height   of the line   of buttons   (38  pixels ).
                    QtCore.QTimer.singleShot(100, lambda: pyzo. main.resizeDocks([dock], [38], QtCore.Qt.Orientation.Vertical))
         except Exception as e :
            print(f"[AI Assistant tool]: Error correcting location: {e}", file=sys.stderr, flush=True)
            
     def showEvent ( self, event :  QtGui.QShowEvent ) -> None:
        QtCore.QTimer.singleShot(1500, ensure_portable_ollama_running)
        super(). showEvent (event)
        
     def closeEvent ( self, event :  QtGui.QCloseEvent ) -> None:
         if hasattr (self, ' ai_panel '):
            self.ai_panel._ stop_existing_worker ()
         kill_ollama_process_tree ()
         event.accept ()

def initialize_ai_assistant_extension ():
    try:
         atexit.register ( kill_ollama_process_tree )
         if hasattr (pyzo. toolManager , " registerTool "):
             pyzo.toolManager.registerTool ( AIAssistantTool )
         elif hasattr (pyzo. toolManager , " register_tool "):
             pyzo.toolManager.register_tool ( AIAssistantTool )
     except Exception as e :
        print(f"[AI-Initializer]: Failed to load extension: {e}", file=sys.stderr, flush=True)

initialize_ai_assistant_extension ()
