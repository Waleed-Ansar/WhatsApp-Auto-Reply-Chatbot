import subprocess
import json
import sys
import time
import threading

class MCPClient:
    def __init__(self, server_script_path):
        self.process = subprocess.Popen(
            [sys.executable, server_script_path],
            creationflags=0x08000000,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=0
        )
        self.request_id = 0

        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stderr_thread.start()
        
        self._initialize()
    
    def _read_stderr(self):
        try:
            for line in self.process.stderr:
                # print(f"[MCP Server] {line.strip()}")
                pass
        except:
            pass
    
    def _send_message(self, message):
        """Send a JSON-RPC message to the server"""
        msg_str = json.dumps(message)
        self.process.stdin.write(msg_str + "\n")
        self.process.stdin.flush()
    
    def _receive_message(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            line = self.process.stdout.readline()
            if line:
                line = line.strip()
                if line:
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            time.sleep(0.01)
        return None
    
    def _initialize(self):
        self.request_id += 1
        init_msg = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "python-client",
                    "version": "1.0.0"
                }
            }
        }
        
        self._send_message(init_msg)
        response = self._receive_message(timeout=5)
        
        if response and "result" in response:
            self._send_message({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })
            time.sleep(0.5)
            print("MCP client initialized successfully")
        else:
            raise Exception(f"Failed to initialize: {response}")
    
    def call_tool(self, name, arguments):
        self.request_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        
        self._send_message(message)
        response = self._receive_message(timeout=30)
        
        if response and "result" in response:
            result = response["result"]
            content = result.get("content", [])
            
            if content and isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    return first_item["text"]
            
            return str(result)
            
        elif response and "error" in response:
            raise Exception(f"Tool call error: {response['error']}")
        else:
            raise Exception(f"No response received from MCP server")
    
    def __del__(self):
        if hasattr(self, 'process') and self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                self.process.kill()