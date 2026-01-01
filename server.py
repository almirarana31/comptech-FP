"""
Flask web server for Javanese Script Translator
Serves the HTML interface and provides translation API
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from ct import Translator, Lexer, TokenType
import sys
import io
from contextlib import redirect_stdout
from enum import Enum

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for local development

translator = Translator(debug=False)


class OutputCapture:
    """Capture stdout for debug output"""
    def __init__(self):
        self.output = []
        self.closed = False
        
    def write(self, text):
        # Capture all output, including newlines and empty strings
        if text:
            self.output.append(str(text))
    
    def flush(self):
        pass
    
    def close(self):
        self.closed = True
    
    def isatty(self):
        return False
    
    def readable(self):
        return False
    
    def writable(self):
        return True
    
    def seekable(self):
        return False
    
    def get_output(self):
        return ''.join(self.output)
    
    def clear(self):
        self.output = []

@app.route('/')
def index():
    """Serve the main HTML page"""
    return app.send_static_file('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    """Translation API endpoint"""
    debug_output = ""
    tokens_data = []
    
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        debug = data.get('debug', False)
        
        if not text:
            return jsonify({
                'error': 'No text provided',
                'latin': '',
                'english': '',
                'analysis': {'words': []},
                'errors': [],
                'debug_output': '',
                'tokens': []
            }), 400
        
        # Set debug mode
        translator.debug = debug
        
        # Capture debug output if debug mode is enabled
        if debug:
            output_capture = OutputCapture()
            old_stdout = sys.stdout
            
            try:
                # Redirect stdout to our capture object
                sys.stdout = output_capture
                
                # Perform translation (this will print all debug info)
                result = translator.translate(text, show_analysis=True)
            finally:
                # Restore stdout
                sys.stdout = old_stdout
            
            debug_output = output_capture.get_output()
            
            # Debug: Print to server console to verify capture (use stderr so it doesn't interfere)
            if debug_output:
                print(f"[SERVER DEBUG] Captured {len(debug_output)} characters of debug output", file=sys.stderr)
                print(f"[SERVER DEBUG] First 200 chars: {debug_output[:200]}", file=sys.stderr)
            else:
                print(f"[SERVER DEBUG] WARNING: No debug output captured!", file=sys.stderr)
            
            # Also capture tokens separately for better display
            lexer = Lexer(text)
            token_num = 0
            while True:
                token = lexer.get_next_token()
                if token.type == TokenType.EOF:
                    break
                tokens_data.append({
                    'num': token_num,
                    'type': token.type.value,
                    'value': token.value,
                    'latin': token.latin,
                    'line': token.line,
                    'column': token.column,
                    'index': token.index
                })
                token_num += 1
        else:
            # Perform translation without capturing output
            result = translator.translate(text, show_analysis=True)
        
        # Format errors for JSON
        errors = []
        if result.get('errors'):
            errors = [{
                'code': e.code,
                'message': e.message,
                'line': e.line,
                'column': e.column,
                'token_value': e.token_value,
                'context': getattr(e, 'context', '')
            } for e in result['errors']]
        
        # Format AST for debug if available
        ast_data = None
        if debug and 'ast' in result:
            ast = result['ast']
            ast_data = format_ast_for_json(ast)
        
        # Extract bytecode from debug output or generate it
        bytecode_data = []
        if debug and 'ast' in result:
            from ct import CodeGenerator
            codegen = CodeGenerator()
            bytecode = codegen.generate(result['ast'])
            bytecode_data = [{
                'opcode': instr.opcode.value,
                'operand': instr.operand
            } for instr in bytecode]
        
        # Serialize analysis data to JSON-serializable format
        analysis_data = format_analysis_for_json(result.get('analysis', {'words': []}))
        
        # Return JSON response with all debug information
        response_data = {
            'javanese': result.get('javanese', ''),
            'latin': result.get('latin', ''),
            'english': result.get('english', ''),
            'analysis': analysis_data,
            'errors': errors
        }
        
        # Add debug information if debug mode is enabled
        if debug:
            response_data['debug_output'] = debug_output
            response_data['tokens'] = tokens_data
            if ast_data:
                response_data['ast'] = ast_data
            if bytecode_data:
                response_data['bytecode'] = bytecode_data
            
            # Add debug metadata for troubleshooting
            response_data['debug_metadata'] = {
                'output_length': len(debug_output),
                'tokens_count': len(tokens_data),
                'has_ast': ast_data is not None,
                'has_bytecode': len(bytecode_data) > 0
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Translation error: {e}", file=sys.stderr)
        print(traceback_str, file=sys.stderr)
        
        return jsonify({
            'error': error_msg,
            'traceback': traceback_str if debug else None,
            'latin': '',
            'english': '',
            'analysis': {'words': []},
            'errors': [],
            'debug_output': debug_output if debug else '',
            'tokens': tokens_data if debug else []
        }), 500


def format_ast_for_json(ast_node):
    """Convert AST node to JSON-serializable format"""
    return {
        'node_type': ast_node.node_type.value,
        'value': ast_node.value,
        'children': [format_ast_for_json(child) for child in ast_node.children]
    }

def format_analysis_for_json(analysis):
    """Convert analysis data to JSON-serializable format"""
    if not analysis or 'words' not in analysis:
        return {'words': []}
    
    words_serialized = []
    for word_info in analysis['words']:
        word_dict = {
            'word': word_info.get('word', ''),
            'meaning': word_info.get('meaning', ''),
            'pos': word_info.get('pos', ''),
            'in_dictionary': word_info.get('in_dictionary', False),
            'morphology': None
        }
        
        # Serialize morphology if present
        if word_info.get('morphology'):
            morph = word_info['morphology']
            word_dict['morphology'] = {
                'root': morph.root if hasattr(morph, 'root') else '',
                'morphemes': [
                    {
                        'type': m.type.value if isinstance(m.type, Enum) else str(m.type),
                        'value': m.value,
                        'meaning': m.meaning
                    }
                    for m in (morph.morphemes if hasattr(morph, 'morphemes') else [])
                ],
                'features': dict(morph.features) if hasattr(morph, 'features') else {}
            }
        
        words_serialized.append(word_dict)
    
    return {'words': words_serialized}

if __name__ == '__main__':
    print("=" * 70)
    print("Javanese Script Translator - Web Server")
    print("=" * 70)
    print("\nStarting server on http://localhost:5000")
    print("Open your browser and navigate to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

