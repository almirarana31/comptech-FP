// API endpoint
const API_URL = 'http://localhost:5000/translate';

// State
let isTranslating = false;
let debugMode = false;

// Handle textarea keydown events
function handleTextareaKeydown(event) {
    // Auto-translate on Enter (but allow Shift+Enter for new line)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        console.log('Enter key pressed, translating...');
        translate();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'Enter' || e.key === 'r')) {
            e.preventDefault();
            translate();
        }
    });
    
    // Auto-resize textarea
    const textarea = document.getElementById('inputText');
    if (textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }
    
    // Ensure translate button has event listener (backup to onclick)
    const translateBtn = document.getElementById('translateBtn');
    if (translateBtn) {
        translateBtn.addEventListener('click', function(e) {
            console.log('Translate button clicked');
            e.preventDefault();
            translate();
        });
    }
});

// Toggle input mode between examples and custom text
function toggleInputMode() {
    const examplesSection = document.getElementById('examplesSection');
    const customSection = document.getElementById('customSection');
    const inputModeRadio = document.querySelector('input[name="inputMode"]:checked');
    
    if (!inputModeRadio) {
        console.error('No input mode selected');
        return;
    }
    
    const inputMode = inputModeRadio.value;
    
    if (inputMode === 'examples') {
        if (examplesSection) examplesSection.style.display = 'block';
        if (customSection) customSection.style.display = 'none';
        // Clear custom text when switching to examples
        const textarea = document.getElementById('inputText');
        if (textarea) textarea.value = '';
    } else {
        if (examplesSection) examplesSection.style.display = 'none';
        if (customSection) customSection.style.display = 'block';
        // Focus on textarea when switching to custom
        setTimeout(() => {
            const textarea = document.getElementById('inputText');
            if (textarea) {
                textarea.focus();
                // Ensure textarea is visible and accessible
                textarea.style.display = 'block';
            }
        }, 100);
    }
}

// Load example text
function loadExample(text) {
    // Switch to custom mode and load the example text
    document.querySelector('input[name="inputMode"][value="custom"]').checked = true;
    toggleInputMode();
    const textarea = document.getElementById('inputText');
    if (textarea) {
        textarea.value = text;
        // Small delay to ensure UI is updated
        setTimeout(() => {
            translate();
        }, 100);
    }
}

// Clear all
function clearAll() {
    document.getElementById('inputText').value = '';
    document.getElementById('latinOutput').textContent = '';
    document.getElementById('englishOutput').textContent = '';
    clearAnalysisTable();
    updateStatus('Cleared');
}

// Toggle debug mode
function toggleDebug() {
    debugMode = document.getElementById('debugMode').checked;
    updateStatus(`Debug mode ${debugMode ? 'enabled' : 'disabled'}`);
    
    // Hide debug card if debug mode is disabled
    if (!debugMode) {
        toggleDebugCard(false);
    }
}

// Show help modal
function showHelp() {
    document.getElementById('helpModal').style.display = 'block';
}

// Close help modal
function closeHelp() {
    document.getElementById('helpModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('helpModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Update status bar
function updateStatus(message, isError = false) {
    const statusBar = document.getElementById('statusBar');
    statusBar.textContent = message;
    statusBar.className = isError ? 'status-bar error' : 'status-bar';
}

// Clear analysis table
function clearAnalysisTable() {
    const tbody = document.getElementById('analysisBody');
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No analysis available. Enter text and translate to see word analysis.</td></tr>';
}

// Update analysis table
function updateAnalysisTable(words) {
    const tbody = document.getElementById('analysisBody');
    tbody.innerHTML = '';
    
    if (!words || words.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No words found.</td></tr>';
        return;
    }
    
    words.forEach(wordInfo => {
        const row = document.createElement('tr');
        const status = wordInfo.in_dictionary ? '✓' : '?';
        const statusClass = wordInfo.in_dictionary ? 'status-found' : 'status-unknown';
        
        row.innerHTML = `
            <td>${escapeHtml(wordInfo.word || '')}</td>
            <td>${escapeHtml(wordInfo.meaning || '')}</td>
            <td>${escapeHtml(wordInfo.pos || '')}</td>
            <td class="${statusClass}">${status}</td>
        `;
        tbody.appendChild(row);
    });
}

// Show/hide debug card
function toggleDebugCard(show) {
    const debugCard = document.getElementById('debugCard');
    if (!debugCard) {
        console.error('Debug card element not found!');
        return;
    }
    
    if (show) {
        debugCard.style.display = 'block';
        console.log('Debug card shown');
        // Scroll to debug card
        setTimeout(() => {
            debugCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    } else {
        debugCard.style.display = 'none';
        console.log('Debug card hidden');
    }
}

// Show debug tab
function showDebugTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.debug-content').forEach(el => {
        el.style.display = 'none';
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.debug-tab').forEach(el => {
        el.classList.remove('active');
    });
    
    // Show selected tab
    const tabMap = {
        'output': 'debugOutput',
        'tokens': 'debugTokens',
        'ast': 'debugAST',
        'bytecode': 'debugBytecode',
        'morphology': 'debugMorphology'
    };
    
    const contentId = tabMap[tabName];
    if (contentId) {
        document.getElementById(contentId).style.display = 'block';
        document.querySelector(`.debug-tab[onclick="showDebugTab('${tabName}')"]`).classList.add('active');
    }
}

// Copy debug output to clipboard
function copyDebugOutput() {
    const debugText = document.getElementById('debugText').textContent;
    navigator.clipboard.writeText(debugText).then(() => {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    });
}

// Update debug output
function updateDebugOutput(debugData) {
    console.log('updateDebugOutput called with:', debugData);
    console.log('debugMode:', debugMode);
    
    if (!debugMode) {
        toggleDebugCard(false);
        return;
    }
    
    if (!debugData) {
        console.warn('No debug data provided');
        toggleDebugCard(false);
        return;
    }
    
    toggleDebugCard(true);
    console.log('Debug card toggled to visible');
    
    // Update console output
    const debugTextElement = document.getElementById('debugText');
    if (!debugTextElement) {
        console.error('debugText element not found in DOM!');
        return;
    }
    
    if (debugData.debug_output && debugData.debug_output.length > 0) {
        console.log('Setting debug text, length:', debugData.debug_output.length);
        debugTextElement.textContent = debugData.debug_output;
        console.log('Debug text set successfully');
    } else {
        console.warn('No debug output available');
        debugTextElement.textContent = 
            'No debug output captured.\n\n' +
            'This might mean:\n' +
            '1. Debug mode was not properly enabled\n' +
            '2. The translation completed without printing debug info\n' +
            '3. There was an issue capturing stdout\n\n' +
            'Check the browser console and server logs for more details.';
    }
    
    // Update tokens table
    if (debugData.tokens && debugData.tokens.length > 0) {
        const tokensBody = document.getElementById('tokensBody');
        tokensBody.innerHTML = '';
        debugData.tokens.forEach(token => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${token.num}</td>
                <td>${escapeHtml(token.type)}</td>
                <td>${escapeHtml(token.value)}</td>
                <td>${escapeHtml(token.latin)}</td>
                <td>L${token.line}:C${token.column}</td>
            `;
            tokensBody.appendChild(row);
        });
    } else {
        document.getElementById('tokensBody').innerHTML = 
            '<tr><td colspan="5" style="text-align: center; color: #858585;">No tokens available.</td></tr>';
    }
    
    // Update AST
    if (debugData.ast) {
        document.getElementById('astText').textContent = formatAST(debugData.ast);
    } else {
        document.getElementById('astText').textContent = 'No AST data available.';
    }
    
    // Update Bytecode
    updateBytecodeTable(debugData.bytecode);
    
    // Update Morphology
    updateMorphologyDisplay(debugData.analysis);
    
    // Reset to output tab
    showDebugTab('output');
}

// Update bytecode table
function updateBytecodeTable(bytecode) {
    const bytecodeBody = document.getElementById('bytecodeBody');
    if (!bytecode || bytecode.length === 0) {
        bytecodeBody.innerHTML = 
            '<tr><td colspan="3" style="text-align: center; color: #858585;">No bytecode available.</td></tr>';
        return;
    }
    
    bytecodeBody.innerHTML = '';
    bytecode.forEach((instr, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index.toString().padStart(2, '0')}</td>
            <td>${escapeHtml(instr.opcode || '')}</td>
            <td>${escapeHtml(instr.operand || '')}</td>
        `;
        bytecodeBody.appendChild(row);
    });
}

// Update morphology display
function updateMorphologyDisplay(analysis) {
    const morphologyContent = document.getElementById('morphologyContent');
    if (!analysis || !analysis.words || analysis.words.length === 0) {
        morphologyContent.innerHTML = '<p style="color: #858585; text-align: center;">No morphology data available.</p>';
        return;
    }
    
    let html = '';
    analysis.words.forEach((wordInfo, index) => {
        html += `<div class="morphology-item">`;
        html += `<h3>Word ${index + 1}: "${escapeHtml(wordInfo.word || '')}"</h3>`;
        html += `<div class="morphology-details">`;
        html += `<p><strong>POS:</strong> ${escapeHtml(wordInfo.pos || 'N/A')}</p>`;
        html += `<p><strong>Meaning:</strong> ${escapeHtml(wordInfo.meaning || 'N/A')}</p>`;
        html += `<p><strong>In Dictionary:</strong> ${wordInfo.in_dictionary ? '✓ Yes' : '? No'}</p>`;
        
        if (wordInfo.morphology) {
            const morph = wordInfo.morphology;
            html += `<p><strong>Root:</strong> ${escapeHtml(morph.root || 'N/A')}</p>`;
            
            if (morph.morphemes && morph.morphemes.length > 0) {
                html += `<p><strong>Morphemes (${morph.morphemes.length}):</strong></p>`;
                html += `<ul class="morpheme-list">`;
                morph.morphemes.forEach(m => {
                    html += `<li><strong>${escapeHtml(m.type || 'N/A')}:</strong> "${escapeHtml(m.value || '')}"`;
                    if (m.meaning) {
                        html += ` <em>(${escapeHtml(m.meaning)})</em>`;
                    }
                    html += `</li>`;
                });
                html += `</ul>`;
            }
            
            if (morph.features && Object.keys(morph.features).length > 0) {
                html += `<p><strong>Features:</strong></p>`;
                html += `<ul class="feature-list">`;
                for (const [key, value] of Object.entries(morph.features)) {
                    html += `<li><strong>${escapeHtml(key)}:</strong> ${escapeHtml(String(value))}</li>`;
                }
                html += `</ul>`;
            }
        }
        
        html += `</div></div>`;
    });
    
    morphologyContent.innerHTML = html;
}

// Format AST for display
function formatAST(astNode, indent = 0) {
    const prefix = '  '.repeat(indent);
    let result = `${prefix}${astNode.node_type}('${astNode.value}')\n`;
    
    if (astNode.children && astNode.children.length > 0) {
        astNode.children.forEach(child => {
            result += formatAST(child, indent + 1);
        });
    }
    
    return result;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Main translate function
async function translate() {
    // Get input text - textarea is always in DOM, just might be hidden
    const inputTextElement = document.getElementById('inputText');
    if (!inputTextElement) {
        console.error('Input textarea not found');
        updateStatus('Error: Input field not found', true);
        return;
    }
    
    let inputText = inputTextElement.value.trim();
    const translateBtn = document.getElementById('translateBtn');
    
    if (!translateBtn) {
        console.error('Translate button not found');
        updateStatus('Error: Translate button not found', true);
        return;
    }
    
    if (!inputText) {
        updateStatus('Please enter Javanese text to translate', true);
        return;
    }
    
    // If we're in examples mode but have text, switch to custom mode
    const inputMode = document.querySelector('input[name="inputMode"]:checked');
    if (inputMode && inputMode.value === 'examples' && inputText) {
        // Switch to custom mode to show the text
        const customModeRadio = document.querySelector('input[name="inputMode"][value="custom"]');
        if (customModeRadio) {
            customModeRadio.checked = true;
            toggleInputMode();
            // Re-read the text after mode switch
            inputText = inputTextElement.value.trim();
        }
    }
    
    if (isTranslating) {
        console.log('Translation already in progress');
        return;
    }
    
    // Disable button and show loading state
    isTranslating = true;
    translateBtn.disabled = true;
    translateBtn.textContent = 'Translating...';
    updateStatus('Translating...');
    
    // Clear previous results
    document.getElementById('latinOutput').textContent = '';
    document.getElementById('englishOutput').textContent = '';
    clearAnalysisTable();
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: inputText,
                debug: debugMode
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Debug: Log the response to see what we're getting
        if (debugMode) {
            console.log('Translation result:', result);
            console.log('Debug output length:', result.debug_output ? result.debug_output.length : 0);
        }
        
        // Update UI with results
        document.getElementById('latinOutput').textContent = result.latin || '';
        document.getElementById('englishOutput').textContent = result.english || '';
        
        // Update analysis table
        if (result.analysis && result.analysis.words) {
            updateAnalysisTable(result.analysis.words);
        }
        
        // Update debug output if debug mode is enabled
        if (debugMode) {
            console.log('Updating debug output with:', {
                has_debug_output: !!result.debug_output,
                debug_output_length: result.debug_output ? result.debug_output.length : 0,
                has_tokens: !!result.tokens,
                tokens_count: result.tokens ? result.tokens.length : 0,
                has_ast: !!result.ast,
                has_bytecode: !!result.bytecode,
                bytecode_count: result.bytecode ? result.bytecode.length : 0,
                debug_metadata: result.debug_metadata
            });
            
            // Show a preview of debug output in console
            if (result.debug_output) {
                console.log('Debug output preview (first 500 chars):', result.debug_output.substring(0, 500));
            }
            
            updateDebugOutput({
                debug_output: result.debug_output || '',
                tokens: result.tokens || [],
                ast: result.ast || null,
                bytecode: result.bytecode || [],
                analysis: result.analysis || { words: [] }
            });
        } else {
            toggleDebugCard(false);
        }
        
        // Show errors if any
        const errors = result.errors || [];
        if (errors.length > 0) {
            updateStatus(`Translation complete with ${errors.length} warning(s)`, true);
            if (debugMode) {
                console.warn('Translation warnings:', errors);
            }
        } else {
            updateStatus('Translation complete');
        }
        
    } catch (error) {
        console.error('Translation error:', error);
        updateStatus(`Error: ${error.message}`, true);
        document.getElementById('latinOutput').textContent = 'Error occurred during translation.';
        document.getElementById('englishOutput').textContent = 'Please check the console for details.';
        
        // Show error in debug output if debug mode is on
        if (debugMode) {
            toggleDebugCard(true);
            document.getElementById('debugText').textContent = 
                `Error: ${error.message}\n\n${error.stack || 'No stack trace available'}`;
            showDebugTab('output');
        }
    } finally {
        // Re-enable button
        isTranslating = false;
        translateBtn.disabled = false;
        translateBtn.textContent = 'Translate →';
    }
}

