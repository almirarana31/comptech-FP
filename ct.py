"""
PROGRAM        -> SENTENCE* EOF

SENTENCE       -> (WORD (SPACE WORD)*) (PUNCTUATION)?

WORD           -> AKSARA_GROUP+

AKSARA_GROUP   -> CONSONANT_GROUP
                | VOWEL_GROUP

VOWEL_GROUP    -> VOWEL

CONSONANT_GROUP ->
      CONSONANT
      CLUSTER*
      VOWEL_MARK?
      FINAL_MARK*
      DEAD_MARK?

CLUSTER        -> PANGKON CONSONANT

VOWEL_MARK     -> VOCAL_DIACRITIC
FINAL_MARK     -> CONSONANT_DIACRITIC
DEAD_MARK      -> PANGKON
"""


from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Tuple
import re

#token definitions
class TokenType(Enum):
    CONSONANT = "CONSONANT"
    VOWEL = "VOWEL"
    VOCAL_DIACRITIC = "VOCAL_DIACRITIC"
    CONSONANT_DIACRITIC = "CONSONANT_DIACRITIC"
    PANGKON = "PANGKON"
    PASANGAN = "PASANGAN"
    SPACE = "SPACE"
    PUNCTUATION = "PUNCTUATION"
    UNKNOWN = "UNKNOWN"
    EOF = "EOF"

@dataclass
class Token:
    #represents single token
    type: TokenType
    value: str
    latin: str
    index: int
    line: int
    column: int

    def pos_str(self) -> str:
        return f"line {self.line}, col {self.column} (idx {self.index})"


# COMPILER DIAGNOSTICS
@dataclass
class CompileError:
    code: str                 # e.g., "LEX001", "SYN001"
    message: str              # human-friendly error
    index: int
    line: int
    column: int
    token_value: str = ""
    context: str = ""         # optional: short input snippet

    def format(self) -> str:
        loc = f"line {self.line}, col {self.column} (idx {self.index})"
        val = f" '{self.token_value}'" if self.token_value else ""
        return f"[{self.code}] {loc}: {self.message}{val}"

class ErrorReporter:
    def __init__(self, source: str):
        self.source = source
        self.errors: List[CompileError] = []

    def add(self, code: str, message: str, token: Token, context_window: int = 12):
        # Create a small context snippet around index (optional, but nice)
        i = max(0, token.index - context_window)
        j = min(len(self.source), token.index + context_window)
        snippet = self.source[i:j].replace("\n", "\\n")

        self.errors.append(
            CompileError(
                code=code,
                message=message,
                index=token.index,
                line=token.line,
                column=token.column,
                token_value=token.value,
                context=snippet
            )
        )

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def print(self):
        if not self.errors:
            return
        print("\n" + "-" * 70)
        print("DIAGNOSTICS")
        print("-" * 70)
        for e in self.errors:
            print("  " + e.format())
            if e.context:
                print(f"      context: {e.context}")



#character mapping
class JavaneseChars:
    #base consonants
    CONSONANTS = {
        'ꦲ': 'h',  'ꦤ': 'n',  'ꦕ': 'c',  'ꦫ': 'r',  'ꦏ': 'k',
        'ꦢ': 'd',  'ꦠ': 't',  'ꦱ': 's',  'ꦮ': 'w',  'ꦭ': 'l',
        'ꦥ': 'p',  'ꦝ': 'dh', 'ꦗ': 'j',  'ꦪ': 'y',  'ꦚ': 'ny',
        'ꦩ': 'm',  'ꦒ': 'g',  'ꦧ': 'b',  'ꦛ': 'th', 'ꦔ': 'ng',
    }

    #independent vowels (Aksara Swara)
    VOWELS = {
        'ꦄ': 'a',
        'ꦆ': 'i',
        'ꦈ': 'u',
        'ꦌ': 'e',
        'ꦎ': 'o',
    }

    #vowel diacritics (Sandhangan Swara)
    VOCAL_DIACRITICS = {
        'ꦶ': 'i',   # wulu
        'ꦸ': 'u',   # suku
        'ꦺ': 'e',   # taling
        'ꦼ': 'e',   # pepet (ê)
        'ꦴ': 'o',   # tarung
        'ꦻ': 'ai',  # taling-tarung (ai)
    }

    #consonant endings (Sandhangan Panyigeg)
    CONSONANT_DIACRITICS = {
        'ꦁ': 'ng',  # cecak
        'ꦂ': 'r',   # layar
        'ꦃ': 'h',   # wignyan
    }

    #pangkon (virama) - removes inherent 'a'
    PANGKON = '꧀'

    #punctuation (Pada)
    PUNCTUATION = {
        '꧊': ',',   # pada lingsa
        '꧋': '.',   # pada lungsi
        '꧈': ',',   # pada pangkat
        '꧉': '.',   # pada guru
    }

    CECAK_TELU = '꦳'

    REKAN_MAP = {
        'ꦏ': 'kh',   # ka + ꦳  → kha
        'ꦢ': 'dz',   # da + ꦳  → dza
        'ꦥ': 'f',    # pa + ꦳  → fa/va
        'ꦗ': 'z',    # ja + ꦳  → za
        'ꦒ': 'gh',   # ga + ꦳  → gha
        'ꦮ': 'v',    # pa + ꦳  → fa/va
    }

# =============================================================================
# REGEX TOKEN SPEC (Formal token definitions)
# =============================================================================

TOKEN_SPECS = [
    ("SPACE",               r"[ \t\r\n]+"),
    ("PUNCTUATION",         r"[꧊꧋꧈꧉]"),
    ("PASANGAN", r"꧀(?:[ꦲꦤꦕꦫꦏꦢꦠꦱꦮꦭꦥꦝꦗꦪꦚꦩꦒꦧꦛꦔ]|[ꦏꦢꦥꦗꦒꦮ]꦳)"),
    ("PANGKON",             r"꧀"),
    ("VOCAL_DIACRITIC",     r"[ꦶꦸꦺꦼꦴꦻ]"),
    ("CONSONANT_DIACRITIC", r"[ꦁꦂꦃ]"),

    # rekan: 2 chars
    ("CONSONANT_REKAN",     r"[ꦏꦢꦥꦗꦒꦮ]꦳"),

    # base consonants: 1 char
    ("CONSONANT_BASE",      r"[ꦲꦤꦕꦫꦏꦢꦠꦱꦮꦭꦥꦝꦗꦪꦚꦩꦒꦧꦛꦔ]"),

    ("VOWEL",               r"[ꦄꦆꦈꦌꦎ]"),
    ("UNKNOWN",             r"."),
]

MASTER_RE = re.compile("|".join(
    f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECS
))



#=============================================================================
# PHASE 1: LEXICAL ANALYSIS
#=============================================================================

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

        # position tracking
        self.line = 1
        self.column = 1

    def _make_token(self, token_type: TokenType, value: str, latin: str,
                    start_index: int, start_line: int, start_col: int) -> Token:
        return Token(
            type=token_type,
            value=value,
            latin=latin,
            index=start_index,
            line=start_line,
            column=start_col
        )

    def _advance_span(self, span: str):
        # update line/column for multi-char tokens (SPACE can be multiple chars)
        for ch in span:
            if ch == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        self.pos += len(span)

    def get_next_token(self) -> Token:
        if self.pos >= len(self.text):
            return self._make_token(
                TokenType.EOF, "", "", self.pos, self.line, self.column
            )

        start_index = self.pos
        start_line = self.line
        start_col = self.column

        m = MASTER_RE.match(self.text, self.pos)
        if not m:
            ch = self.text[self.pos]
            tok = self._make_token(
                TokenType.UNKNOWN, ch, ch, start_index, start_line, start_col
            )
            self._advance_span(ch)
            return tok

        kind = m.lastgroup
        value = m.group(kind)

        # -------------------------------
        # TOKEN TYPE MAPPING
        # -------------------------------
        if kind in ("CONSONANT_BASE", "CONSONANT_REKAN"):
            ttype = TokenType.CONSONANT
        elif kind == "PASANGAN":
            ttype = TokenType.PASANGAN
        else:
            ttype = TokenType[kind] if kind in TokenType.__members__ else TokenType.UNKNOWN

        # -------------------------------
        # LATIN TRANSLITERATION
        # -------------------------------
        latin = ""

        if ttype == TokenType.SPACE:
            latin = " "

        elif ttype == TokenType.PUNCTUATION:
            latin = JavaneseChars.PUNCTUATION.get(value, value)

        elif ttype == TokenType.VOWEL:
            latin = JavaneseChars.VOWELS.get(value, "")

        elif ttype == TokenType.VOCAL_DIACRITIC:
            latin = JavaneseChars.VOCAL_DIACRITICS.get(value, "")

        elif ttype == TokenType.CONSONANT_DIACRITIC:
            latin = JavaneseChars.CONSONANT_DIACRITICS.get(value, "")

        elif ttype == TokenType.CONSONANT:
            if len(value) == 2 and value.endswith(JavaneseChars.CECAK_TELU):
                base = value[0]
                latin = JavaneseChars.REKAN_MAP.get(
                    base, JavaneseChars.CONSONANTS.get(base, "")
                )
            else:
                latin = JavaneseChars.CONSONANTS.get(value, "")

        elif ttype == TokenType.PASANGAN:
            # value = ꧀ + consonant
            cons = value[1:]
            if len(cons) == 2 and cons.endswith(JavaneseChars.CECAK_TELU):
                base = cons[0]
                latin = JavaneseChars.REKAN_MAP.get(
                    base, JavaneseChars.CONSONANTS.get(base, "")
                )
            else:
                latin = JavaneseChars.CONSONANTS.get(cons, "")

        elif ttype == TokenType.PANGKON:
            latin = ""  # handled grammatically, not phonetically

        else:
            latin = value

        tok = self._make_token(
            ttype, value, latin, start_index, start_line, start_col
        )
        self._advance_span(value)
        return tok

#=============================================================================
# PHASE 2: SYNTAX ANALYSIS (PARSER) + AST GENERATION
#=============================================================================

class ASTNodeType(Enum):
    PROGRAM = "PROGRAM"
    SENTENCE = "SENTENCE"
    WORD = "WORD"
    SYLLABLE = "SYLLABLE"
    PUNCTUATION = "PUNCTUATION"
    SPACE = "SPACE"

@dataclass
class ASTNode:
    """Abstract Syntax Tree Node"""
    node_type: ASTNodeType
    value: str = ""
    children: List['ASTNode'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def __repr__(self):
        if self.children:
            return f"{self.node_type.value}({self.value}, {len(self.children)} children)"
        return f"{self.node_type.value}({self.value})"


class Parser:
    def __init__(self, lexer, debug=False, reporter: Optional[ErrorReporter] = None):
        self.lexer = lexer
        self.debug = debug
        self.reporter = reporter
        self.current_token = self.lexer.get_next_token()

    def advance(self):
        """Move to the next token (parser-side helper)."""
        self.current_token = self.lexer.get_next_token()

    def error(self, code: str, message: str, token: Optional[Token] = None):
        tok = token if token is not None else self.current_token
        if self.reporter:
            self.reporter.add(code, message, tok)
        if self.debug:
            print(f"[ERROR {code}] {message} at {tok.pos_str()} value='{tok.value}'")

    def eat(self, token_type: TokenType):
        if self.debug:
            print(f"[PARSER] eat(): expected={token_type}, got={self.current_token}")

        if self.current_token.type == token_type:
            self.advance()
            return True

        # Record syntax error, then recover by skipping the unexpected token
        self.error(
            "SYN001",
            f"Unexpected token, expected {token_type.value}",
            self.current_token
        )
        self.advance()
        return False

    def parse_consonant_group(self) -> ASTNode:
        """
        Grammar:
          CONSONANT_GROUP ->
              CONSONANT
              CLUSTER*
              VOWEL_MARK?
              FINAL_MARK*
              DEAD_MARK?

          CLUSTER      -> PANGKON CONSONANT
          VOWEL_MARK   -> VOCAL_DIACRITIC
          FINAL_MARK   -> CONSONANT_DIACRITIC
          DEAD_MARK    -> PANGKON

        Implementation detail:
          - CLUSTER is lexed as PASANGAN (single token = '꧀' + consonant),
            so CLUSTER* is implemented as: while PASANGAN: eat(PASANGAN)
        """
        # CONSONANT
        base = self.current_token.latin
        self.eat(TokenType.CONSONANT)

        # CLUSTER*  (implemented as PASANGAN*)
        clusters = []
        while self.current_token.type == TokenType.PASANGAN:
            # PASANGAN already encodes pangkon+consonant
            clusters.append(self.current_token.latin)
            self.eat(TokenType.PASANGAN)

        # VOWEL_MARK?  (VOCAL_DIACRITIC optional; otherwise inherent 'a')
        vowel = "a"   # inherent vowel unless changed
        if self.current_token.type == TokenType.VOCAL_DIACRITIC:
            vowel = self.current_token.latin
            self.eat(TokenType.VOCAL_DIACRITIC)

        # FINAL_MARK*  (zero or more CONSONANT_DIACRITIC)
        finals = ""
        while self.current_token.type == TokenType.CONSONANT_DIACRITIC:
            finals += self.current_token.latin
            self.eat(TokenType.CONSONANT_DIACRITIC)

        # DEAD_MARK?  (optional ending PANGKON)
        dead = False
        if self.current_token.type == TokenType.PANGKON:
            # end pangkon kills vowel
            dead = True
            self.eat(TokenType.PANGKON)

        # Build romanization
        core = base + "".join(clusters)
        if dead:
            out = core + finals
        else:
            out = core + vowel + finals

        # Make AST richer (optional, but recommended)
        node = ASTNode(ASTNodeType.SYLLABLE, out)
        return node

    def parse_vowel_syllable(self) -> str:
        result = self.current_token.latin
        self.eat(TokenType.VOWEL)
        return result

    def parse_syllable(self) -> Optional[ASTNode]:
        """
        Grammar:
          AKSARA_GROUP -> CONSONANT_GROUP | VOWEL_GROUP
          VOWEL_GROUP  -> VOWEL

        Implementation:
          - if token starts with CONSONANT: parse_consonant_group()
          - if token is VOWEL: parse_vowel_syllable()
          - otherwise: emit syntax errors (recovery)
        """

        # ✅ Valid syllable starters
        if self.current_token.type == TokenType.CONSONANT:
            return self.parse_consonant_group()

        if self.current_token.type == TokenType.VOWEL:
            syllable_text = self.parse_vowel_syllable()
            return ASTNode(ASTNodeType.SYLLABLE, syllable_text)

        # ❌ PASANGAN cannot start a syllable
        if self.current_token.type == TokenType.PASANGAN:
            self.error(
                "SYN003",
                "PASANGAN cannot appear without a base consonant",
                self.current_token
            )
            self.advance()
            return None

        # ❌ Diacritics / pangkon without base consonant
        if self.current_token.type in [
            TokenType.VOCAL_DIACRITIC,
            TokenType.CONSONANT_DIACRITIC,
            TokenType.PANGKON
        ]:
            self.error(
                "SYN002",
                "Invalid diacritic order: diacritic/pangkon cannot appear without a base consonant",
                self.current_token
            )
            self.advance()
            return None

        return None

    def parse_word(self) -> ASTNode:
        """
        Grammar:
          WORD -> AKSARA_GROUP+

        Implementation:
          - repeatedly parse_syllable() (your syllable corresponds to AKSARA_GROUP)
          - stop at SPACE / PUNCTUATION / EOF
          - error recovery skips bad tokens and continues
        """
        word_node = ASTNode(ASTNodeType.WORD, "")

        while self.current_token.type in [
                TokenType.CONSONANT, TokenType.VOWEL,
                TokenType.VOCAL_DIACRITIC, TokenType.CONSONANT_DIACRITIC,
                TokenType.PANGKON
            ]:
            syllable_node = self.parse_syllable()
            if syllable_node is None:
                # recovery: keep going
                continue
            word_node.children.append(syllable_node)
            word_node.value += syllable_node.value

            # Stop if next is space/punct/eof
            if self.current_token.type in [TokenType.SPACE, TokenType.PUNCTUATION, TokenType.EOF]:
                break

        return word_node

    def parse_sentence(self) -> ASTNode:
        """
        Grammar:
          SENTENCE -> (WORD (SPACE WORD)*) (PUNCTUATION)?

        Implementation:
          - While not PUNCTUATION/EOF:
              parse WORD whenever the token stream looks like a word start
              consume SPACE tokens between words
          - After loop: optionally consume a single PUNCTUATION
        """
        sentence_node = ASTNode(ASTNodeType.SENTENCE, "")

        while self.current_token.type not in [TokenType.PUNCTUATION, TokenType.EOF]:
            if self.current_token.type in [
                TokenType.CONSONANT,
                TokenType.VOWEL,
                TokenType.VOCAL_DIACRITIC,
                TokenType.CONSONANT_DIACRITIC,
                TokenType.PANGKON,
            ]:
                word = self.parse_word()
                if word.value:
                    sentence_node.children.append(word)
                    sentence_node.value += word.value

            elif self.current_token.type == TokenType.PASANGAN:
                # ❌ PASANGAN cannot start a word
                self.error(
                    "SYN003",
                    "PASANGAN cannot start a word",
                    self.current_token
                )
                self.advance()

            elif self.current_token.type == TokenType.SPACE:
                space_node = ASTNode(ASTNodeType.SPACE, self.current_token.latin)
                sentence_node.children.append(space_node)
                sentence_node.value += " "
                self.eat(TokenType.SPACE)

            elif self.current_token.type == TokenType.UNKNOWN:
                # Illegal character
                self.error("LEX001", "Illegal character", self.current_token)
                self.advance()

            else:
                # Generic known-but-unexpected token
                self.error("SYN006", "Unexpected token in sentence", self.current_token)
                self.advance()

        # Handle punctuation
        if self.current_token.type == TokenType.PUNCTUATION:
            punct_node = ASTNode(ASTNodeType.PUNCTUATION, self.current_token.latin)
            sentence_node.children.append(punct_node)
            sentence_node.value += self.current_token.latin
            self.eat(TokenType.PUNCTUATION)

        return sentence_node

    def parse(self) -> ASTNode:
        """
          Grammar: PROGRAM -> SENTENCE* EOF
          Implementation:
            - loop until EOF, repeatedly parse_sentence()
            - error recovery allows unexpected tokens, but the "happy path"
              corresponds to SENTENCE*.
          """
        program_node = ASTNode(ASTNodeType.PROGRAM, "")

        while self.current_token.type != TokenType.EOF:
            if self.current_token.type in [
                TokenType.CONSONANT,
                TokenType.VOWEL,
                TokenType.SPACE,
                TokenType.VOCAL_DIACRITIC,
                TokenType.CONSONANT_DIACRITIC,
                TokenType.PANGKON,
                TokenType.UNKNOWN,
            ]:
                sentence = self.parse_sentence()
                program_node.children.append(sentence)
                program_node.value += sentence.value
            elif self.current_token.type == TokenType.PASANGAN:
                self.error("SYN003", "PASANGAN cannot start a sentence", self.current_token)
                self.advance()
            else:
                self.error("SYN000", "Unexpected token at program level", self.current_token)
                self.advance()

        if self.debug:
            print(f"[PARSER] AST built: {program_node}")

        return program_node


class OrthographyValidator:
    """
    Validates orthography rules using token stream.
    This is a post-lexing validation pass (like a compiler static check).
    """
    def __init__(self, source: str, reporter: ErrorReporter, debug: bool = False):
        self.source = source
        self.reporter = reporter
        self.debug = debug

    def validate(self) -> None:
        lexer = Lexer(self.source)

        # State for "current base consonant syllable"
        have_base = False
        seen_vowel = False
        seen_pangkon = False
        seen_final = False  # consonant diacritic like ꦁ ꦂ ꦃ

        while True:
            tok = lexer.get_next_token()
            if tok.type == TokenType.EOF:
                break

            # Reset syllable context at boundaries
            if tok.type in (TokenType.SPACE, TokenType.PUNCTUATION):
                have_base = False
                seen_vowel = False
                seen_pangkon = False
                seen_final = False
                continue

            if tok.type == TokenType.CONSONANT:
                # Start new base syllable context
                have_base = True
                seen_vowel = False
                seen_pangkon = False
                seen_final = False
                continue

            # ✅ PASANGAN handling (ADD HERE)
            if tok.type == TokenType.PASANGAN:
                # PASANGAN must follow a base consonant
                if not have_base:
                    self.reporter.add(
                        "ORT007",
                        "PASANGAN must follow a base consonant",
                        tok
                    )
                # PASANGAN extends the current consonant cluster
                continue

            if tok.type == TokenType.VOWEL:
                # Independent vowel (Aksara Swara) stands alone; reset context
                have_base = False
                seen_vowel = False
                seen_pangkon = False
                seen_final = False
                continue

            if tok.type == TokenType.VOCAL_DIACRITIC:
                # Rule: vowel diacritic must follow a consonant (base)
                if not have_base:
                    self.reporter.add("ORT001", "Vowel diacritic must follow a base consonant", tok)
                if seen_vowel:
                    self.reporter.add("ORT003", "Multiple vowel diacritics on one base consonant", tok)
                if seen_pangkon:
                    self.reporter.add("ORT004", "Vowel diacritic cannot appear after pangkon", tok)

                seen_vowel = True
                continue

            if tok.type == TokenType.PANGKON:
                if not have_base:
                    self.reporter.add("ORT002", "Pangkon must follow a base consonant", tok)
                seen_pangkon = True
                continue

            if tok.type == TokenType.CONSONANT_DIACRITIC:
                if not have_base:
                    self.reporter.add("ORT001", "Final consonant mark must follow a base consonant", tok)
                if seen_pangkon:
                    self.reporter.add("ORT005", "Final consonant mark cannot appear after pangkon", tok)

                seen_final = True
                continue

            if tok.type == TokenType.UNKNOWN:
                self.reporter.add("LEX001", "Illegal character", tok)
                continue


#=============================================================================
# PHASE 3: SEMANTIC ANALYSIS (MORPHOLOGICAL + SYNTACTIC)
#=============================================================================

class MorphemeType(Enum):
    PREFIX = "PREFIX"
    ROOT = "ROOT"
    SUFFIX = "SUFFIX"
    REDUPLICATION = "REDUPLICATION"

@dataclass
class Morpheme:
    """Represents a morphological unit"""
    type: MorphemeType
    value: str
    meaning: Optional[str] = None

@dataclass
class WordAnalysis:
    """Complete morphological analysis of a word"""
    original: str
    morphemes: List[Morpheme]
    root: str
    pos_tag: str  # Part of speech
    features: dict

class MorphologicalAnalyzer:
    """
    Analyzes Javanese morphology (affixes, roots, reduplication)
    """

    # Javanese prefixes and their meanings
    PREFIXES = {
        'ng': ('active verb marker', 'ng-'),
        'n': ('active verb marker (nasal)', 'n-'),
        'm': ('active verb marker (nasal)', 'm-'),
        'ny': ('active verb marker (nasal)', 'ny-'),
        'di': ('passive voice', 'di-'),
        'ke': ('accidental/involuntary', 'ke-'),
        'pa': ('causative/nominalizer', 'pa-'),
        'pi': ('causative', 'pi-'),
        'sa': ('one/unity', 'sa-'),
        'pra': ('pre-', 'pra-'),
        'tar': ('most', 'tar-'),
    }

    # Javanese suffixes
    SUFFIXES = {
        'an': ('noun/locative suffix', '-an'),
        'en': ('imperative/passive', '-en'),
        'i': ('locative/directive', '-i'),
        'ake': ('causative/benefactive', '-ake'),
        'na': ('imperative', '-na'),
        'e': ('definite marker', '-e'),
    }

    # Circumfixes (prefix + suffix combinations)
    CIRCUMFIXES = {
        ('ke', 'an'): ('abstract noun, state of being', 'ke-...-an'),
        ('pa', 'an'): ('place/instrument', 'pa-...-an'),
        ('ka', 'an'): ('abstract noun', 'ka-...-an'),
        ('pi', 'an'): ('nominalizer', 'pi-...-an'),
    }

    def analyze(self, word: str) -> WordAnalysis:
        """Perform complete morphological analysis"""
        if not word:
            return WordAnalysis(word, [], word, 'UNKNOWN', {})

        morphemes = []
        remaining = word
        root = word
        features = {}
        pos_tag = 'NOUN'  # Default

        # Check for reduplication (e.g., "mlaku-mlaku" -> "mlaku" repeated)
        if '-' in word:
            parts = word.split('-')
            if len(parts) == 2 and parts[0] == parts[1]:
                morphemes.append(Morpheme(MorphemeType.REDUPLICATION, parts[0], 'plurality/continuity'))
                root = parts[0]
                features['reduplication'] = True
                return WordAnalysis(word, morphemes, root, 'VERB', features)

        # Check for circumfixes first
        for (prefix, suffix), (meaning, pattern) in self.CIRCUMFIXES.items():
            if remaining.startswith(prefix) and remaining.endswith(suffix):
                morphemes.append(Morpheme(MorphemeType.PREFIX, prefix, meaning))
                morphemes.append(Morpheme(MorphemeType.SUFFIX, suffix, meaning))
                root = remaining[len(prefix):-len(suffix)]
                morphemes.insert(1, Morpheme(MorphemeType.ROOT, root))
                pos_tag = 'NOUN'
                features['circumfix'] = pattern
                return WordAnalysis(word, morphemes, root, pos_tag, features)

        # Check for prefixes
        for prefix, (meaning, pattern) in self.PREFIXES.items():
            if remaining.startswith(prefix):
                morphemes.append(Morpheme(MorphemeType.PREFIX, prefix, meaning))
                remaining = remaining[len(prefix):]
                pos_tag = 'VERB'
                features['voice'] = 'active' if prefix in ['ng', 'n', 'm', 'ny'] else 'passive'
                break

        # Check for suffixes
        for suffix, (meaning, pattern) in self.SUFFIXES.items():
            if remaining.endswith(suffix):
                morphemes.append(Morpheme(MorphemeType.SUFFIX, suffix, meaning))
                root = remaining[:-len(suffix)]
                remaining = root
                features['suffix'] = pattern
                break

        # What's left is the root
        if not any(m.type == MorphemeType.ROOT for m in morphemes):
            root = remaining if remaining else word
            morphemes.insert(0 if not morphemes else len([m for m in morphemes if m.type == MorphemeType.PREFIX]),
                           Morpheme(MorphemeType.ROOT, root))

        return WordAnalysis(word, morphemes, root, pos_tag, features)


class SymbolTable:
    """
    Symbol table for word meanings (like compiler symbol tables)
    Stores lexical entries with morphosyntactic information
    """
    def __init__(self):
        self.entries = {
            # Pronouns
            'aku': {'pos': 'PRON', 'english': 'I', 'person': '1', 'register': 'ngoko'},
            'kula': {'pos': 'PRON', 'english': 'I', 'person': '1', 'register': 'krama'},
            'kowe': {'pos': 'PRON', 'english': 'you', 'person': '2', 'register': 'ngoko'},
            'sampeyan': {'pos': 'PRON', 'english': 'you', 'person': '2', 'register': 'krama'},
            'dheweke': {'pos': 'PRON', 'english': 'he/she', 'person': '3'},
            'awakdewe': {'pos': 'PRON', 'english': 'we', 'person': '1PL'},
            'haku': {'pos': 'PRON', 'english': 'I', 'person': '1', 'register': 'ngoko'},

            # Common verbs (roots)
            'mangan': {'pos': 'VERB', 'english': 'eat', 'type': 'action'},
            'mang': {'pos': 'V-ROOT', 'english': 'eat', 'type': 'action'},
            'ngombe': {'pos': 'VERB', 'english': 'drink', 'type': 'action'},
            'ombe': {'pos': 'V-ROOT', 'english': 'drink', 'type': 'action'},
            'turu': {'pos': 'VERB', 'english': 'sleep', 'type': 'action'},
            'tangi': {'pos': 'VERB', 'english': 'wake up', 'type': 'action'},
            'mlaku': {'pos': 'VERB', 'english': 'walk', 'type': 'action'},
            'laku': {'pos': 'V-ROOT', 'english': 'walk', 'type': 'action'},
            'mlayu': {'pos': 'VERB', 'english': 'run', 'type': 'action'},
            'layu': {'pos': 'V-ROOT', 'english': 'run', 'type': 'action'},
            'lungguh': {'pos': 'VERB', 'english': 'sit', 'type': 'action'},
            'ngadeg': {'pos': 'VERB', 'english': 'stand', 'type': 'action'},
            'adeg': {'pos': 'V-ROOT', 'english': 'stand', 'type': 'action'},
            'sinau': {'pos': 'VERB', 'english': 'study', 'type': 'action'},
            'mulih': {'pos': 'VERB', 'english': 'go home', 'type': 'motion'},
            'teka': {'pos': 'VERB', 'english': 'come', 'type': 'motion'},
            'lunga': {'pos': 'VERB', 'english': 'go', 'type': 'motion'},
            'tuku': {'pos': 'VERB', 'english': 'buy', 'type': 'transaction'},
            'nuku': {'pos': 'VERB', 'english': 'buy', 'type': 'transaction'},
            'adol': {'pos': 'VERB', 'english': 'sell', 'type': 'transaction'},
            'dodol': {'pos': 'VERB', 'english': 'sell', 'type': 'transaction'},

            # Common nouns
            'sega': {'pos': 'NOUN', 'english': 'rice', 'type': 'food'},
            'sego': {'pos': 'NOUN', 'english': 'rice', 'type': 'food'},
            'banyu': {'pos': 'NOUN', 'english': 'water', 'type': 'liquid'},
            'omah': {'pos': 'NOUN', 'english': 'house', 'type': 'place'},
            'griya': {'pos': 'NOUN', 'english': 'house', 'type': 'place', 'register': 'krama'},
            'sekolah': {'pos': 'NOUN', 'english': 'school', 'type': 'place'},
            'buku': {'pos': 'NOUN', 'english': 'book', 'type': 'object'},
            'guru': {'pos': 'NOUN', 'english': 'teacher', 'type': 'person'},
            'murid': {'pos': 'NOUN', 'english': 'student', 'type': 'person'},
            'siswa': {'pos': 'NOUN', 'english': 'student', 'type': 'person'},
            'wong': {'pos': 'NOUN', 'english': 'person', 'type': 'person'},
            'bocah': {'pos': 'NOUN', 'english': 'child', 'type': 'person'},
            'kanca': {'pos': 'NOUN', 'english': 'friend', 'type': 'person'},
            'bapak': {'pos': 'NOUN', 'english': 'father', 'type': 'person'},
            'ibu': {'pos': 'NOUN', 'english': 'mother', 'type': 'person'},

            # Adjectives
            'apik': {'pos': 'ADJ', 'english': 'good', 'type': 'quality'},
            'becik': {'pos': 'ADJ', 'english': 'good', 'type': 'quality', 'register': 'krama'},
            'ala': {'pos': 'ADJ', 'english': 'bad', 'type': 'quality'},
            'awon': {'pos': 'ADJ', 'english': 'bad', 'type': 'quality', 'register': 'krama'},
            'gedhe': {'pos': 'ADJ', 'english': 'big', 'type': 'size'},
            'ageng': {'pos': 'ADJ', 'english': 'big', 'type': 'size', 'register': 'krama'},
            'cilik': {'pos': 'ADJ', 'english': 'small', 'type': 'size'},
            'alit': {'pos': 'ADJ', 'english': 'small', 'type': 'size', 'register': 'krama'},
            'dhuwur': {'pos': 'ADJ', 'english': 'tall', 'type': 'dimension'},
            'inggil': {'pos': 'ADJ', 'english': 'tall', 'type': 'dimension', 'register': 'krama'},
            'cendhek': {'pos': 'ADJ', 'english': 'short', 'type': 'dimension'},
            'abot': {'pos': 'ADJ', 'english': 'heavy', 'type': 'weight'},
            'entheng': {'pos': 'ADJ', 'english': 'light', 'type': 'weight'},

            # Time words
            'esuk': {'pos': 'NOUN', 'english': 'morning', 'type': 'time'},
            'enjing': {'pos': 'NOUN', 'english': 'morning', 'type': 'time', 'register': 'krama'},
            'awan': {'pos': 'NOUN', 'english': 'noon', 'type': 'time'},
            'siyang': {'pos': 'NOUN', 'english': 'noon', 'type': 'time', 'register': 'krama'},
            'sore': {'pos': 'NOUN', 'english': 'afternoon', 'type': 'time'},
            'sonten': {'pos': 'NOUN', 'english': 'afternoon', 'type': 'time', 'register': 'krama'},
            'bengi': {'pos': 'NOUN', 'english': 'night', 'type': 'time'},
            'dalu': {'pos': 'NOUN', 'english': 'night', 'type': 'time', 'register': 'krama'},
            'saiki': {'pos': 'ADV', 'english': 'now', 'type': 'time'},
            'samenika': {'pos': 'ADV', 'english': 'now', 'type': 'time', 'register': 'krama'},
            'sesuk': {'pos': 'ADV', 'english': 'tomorrow', 'type': 'time'},
            'mbenjang': {'pos': 'ADV', 'english': 'tomorrow', 'type': 'time', 'register': 'krama'},
            'wingi': {'pos': 'ADV', 'english': 'yesterday', 'type': 'time'},
            'kala': {'pos': 'ADV', 'english': 'yesterday', 'type': 'time', 'register': 'krama'},

            # Common phrases
            'sugeng': {'pos': 'ADJ', 'english': 'good', 'type': 'greeting'},
            'nuwun': {'pos': 'INTJ', 'english': 'thank you', 'type': 'courtesy'},
            'matur': {'pos': 'VERB', 'english': 'say/tell', 'register': 'krama'},
            'inggih': {'pos': 'PART', 'english': 'yes', 'register': 'krama'},
            'nggih': {'pos': 'PART', 'english': 'yes', 'register': 'krama'},
            'mboten': {'pos': 'PART', 'english': 'no', 'register': 'krama'},
            'punapa': {'pos': 'PRON', 'english': 'what', 'type': 'question', 'register': 'krama'},

            # Islamic/religious terms
            'zakat': {'pos': 'NOUN', 'english': 'alms', 'type': 'religious'},
            'fajar': {'pos': 'NOUN', 'english': 'dawn', 'type': 'time'},
            'ghaib': {'pos': 'ADJ', 'english': 'unseen', 'type': 'religious'},
            'sholat': {'pos': 'NOUN', 'english': 'prayer', 'type': 'religious'},
            'solat': {'pos': 'NOUN', 'english': 'prayer', 'type': 'religious'},
            'puasa': {'pos': 'NOUN', 'english': 'fasting', 'type': 'religious'},
            'pasa': {'pos': 'NOUN', 'english': 'fasting', 'type': 'religious'},

            # Numbers
            'siji': {'pos': 'NUM', 'english': 'one', 'value': 1},
            'loro': {'pos': 'NUM', 'english': 'two', 'value': 2},
            'telu': {'pos': 'NUM', 'english': 'three', 'value': 3},
            'papat': {'pos': 'NUM', 'english': 'four', 'value': 4},
            'lima': {'pos': 'NUM', 'english': 'five', 'value': 5},
            'gangsal': {'pos': 'NUM', 'english': 'five', 'value': 5, 'register': 'krama'},
            'enem': {'pos': 'NUM', 'english': 'six', 'value': 6},
            'pitu': {'pos': 'NUM', 'english': 'seven', 'value': 7},
            'wolu': {'pos': 'NUM', 'english': 'eight', 'value': 8},
            'sanga': {'pos': 'NUM', 'english': 'nine', 'value': 9},
            'sepuluh': {'pos': 'NUM', 'english': 'ten', 'value': 10},
            'sedasa': {'pos': 'NUM', 'english': 'ten', 'value': 10, 'register': 'krama'},

            # Question words
            'apa': {'pos': 'PRON', 'english': 'what', 'type': 'question'},
            'sapa': {'pos': 'PRON', 'english': 'who', 'type': 'question'},
            'sinten': {'pos': 'PRON', 'english': 'who', 'type': 'question', 'register': 'krama'},
            'ngendi': {'pos': 'PRON', 'english': 'where', 'type': 'question'},
            'pundi': {'pos': 'PRON', 'english': 'where', 'type': 'question', 'register': 'krama'},
            'kapan': {'pos': 'PRON', 'english': 'when', 'type': 'question'},
            'piye': {'pos': 'PRON', 'english': 'how', 'type': 'question'},
            'kepiye': {'pos': 'PRON', 'english': 'how', 'type': 'question'},
            'pira': {'pos': 'PRON', 'english': 'how much/many', 'type': 'question'},
        }

    def lookup(self, word: str) -> Optional[dict]:
        """Look up word in symbol table"""
        return self.entries.get(word.lower())

    def add_entry(self, word: str, info: dict):
        """Add new entry to symbol table"""
        self.entries[word.lower()] = info


class SemanticAnalyzer:
    """
    Performs semantic analysis on the AST
    - Morphological analysis
    - Word meaning lookup
    - Context analysis
    """
    def __init__(self):
        self.morphological_analyzer = MorphologicalAnalyzer()
        self.symbol_table = SymbolTable()

    def analyze_word(self, word_str: str) -> dict:
        """Analyze a single word semantically"""
        # First, try direct lookup
        entry = self.symbol_table.lookup(word_str)

        if entry:
            return {
                'word': word_str,
                'meaning': entry.get('english', ''),
                'pos': entry.get('pos', 'UNKNOWN'),
                'morphology': None,
                'in_dictionary': True
            }

        # If not found, perform morphological analysis
        morph_analysis = self.morphological_analyzer.analyze(word_str)

        # Try to look up the root
        root_entry = self.symbol_table.lookup(morph_analysis.root)

        meaning = ''
        if root_entry:
            meaning = root_entry.get('english', '')
            # Add affix meanings
            for morpheme in morph_analysis.morphemes:
                if morpheme.type in [MorphemeType.PREFIX, MorphemeType.SUFFIX]:
                    if morpheme.meaning:
                        meaning = f"{morpheme.meaning} + {meaning}"

        return {
            'word': word_str,
            'meaning': meaning if meaning else f'[{word_str}]',
            'pos': morph_analysis.pos_tag,
            'morphology': morph_analysis,
            'in_dictionary': root_entry is not None
        }

    def analyze_ast(self, ast: ASTNode) -> dict:
        """Analyze the entire AST"""
        results = {
            'words': [],
            'analysis': {}
        }

        def traverse(node):
            if node.node_type == ASTNodeType.WORD:
                word_analysis = self.analyze_word(node.value)
                results['words'].append(word_analysis)
                results['analysis'][node.value] = word_analysis

            for child in node.children:
                traverse(child)

        traverse(ast)
        return results


#=============================================================================
# PHASE 4: CODE GENERATION / TRANSLATION
#=============================================================================

class Translator:
    """
    Generates final output (translation to Latin/English)
    """
    def __init__(self, debug: bool = False):
        self.semantic_analyzer = SemanticAnalyzer()
        self.debug = debug

    def translate(self, javanese_text: str, show_analysis: bool = False) -> dict:
        """
        Main translation function
        Returns: dict with latin text, english translation, and optional analysis
        """
        reporter = ErrorReporter(javanese_text)
        if self.debug:
            print("\n" + "="*70)
            print("DEBUG MODE - COMPILATION PROCESS")
            print("="*70)
            print(f"\nInput: {javanese_text}")
            print(f"Length: {len(javanese_text)} characters")

        # Phase 1: Lexical Analysis
        if self.debug:
            print("\n" + "-"*70)
            print("PHASE 1: LEXICAL ANALYSIS (Tokenization)")
            print("-"*70)

        lexer = Lexer(javanese_text)
        tokens = []

        if self.debug:
            temp_lexer = Lexer(javanese_text)
            token_num = 0
            while True:
                token = temp_lexer.get_next_token()
                tokens.append(token)
                if token.type == TokenType.EOF:
                    break
                print(f"  Token {token_num:2d}: {token.type.value:20s} | "
                  f"Value: '{token.value}' | Latin: '{token.latin}' | "
                  f"Pos: {token.pos_str()}")
                token_num += 1
            print(f"\n  Total tokens: {len(tokens) - 1} (excluding EOF)")

        # Phase 2: Syntax Analysis (Parsing)
        if self.debug:
            print("\n" + "-"*70)
            print("PHASE 2: SYNTAX ANALYSIS (Parsing & AST Generation)")
            print("-"*70)

        validator = OrthographyValidator(javanese_text, reporter, debug=self.debug)
        validator.validate()
        if self.debug and reporter.has_errors():
            reporter.print()
        lexer = Lexer(javanese_text)  # Reset lexer
        parser = Parser(lexer, debug=self.debug, reporter=reporter)

        try:
            ast = parser.parse()
            if self.debug:
                print("\n  AST Structure:")
                self.print_ast_pretty(ast)
                print(f"\n  Parsed text: '{ast.value}'")
            if reporter.has_errors():
                reporter.print()
        except Exception as e:
            if self.debug:
                print(f"\n  ❌ PARSING ERROR: {e}")
                import traceback
                traceback.print_exc()
            raise

        # Phase 3: Semantic Analysis
        if self.debug:
            print("\n" + "-"*70)
            print("PHASE 3: SEMANTIC ANALYSIS (Morphology & Meaning)")
            print("-"*70)

        try:
            semantic_results = self.semantic_analyzer.analyze_ast(ast)

            if self.debug:
                print(f"\n  Words found: {len(semantic_results['words'])}")
                for i, word_info in enumerate(semantic_results['words'], 1):
                    print(f"\n  Word {i}: '{word_info['word']}'")
                    print(f"    → POS: {word_info['pos']}")
                    print(f"    → Meaning: {word_info['meaning']}")
                    print(f"    → In dictionary: {word_info['in_dictionary']}")

                    if word_info['morphology']:
                        morph = word_info['morphology']
                        print(f"    → Root: '{morph.root}'")
                        print(f"    → Morphemes: {len(morph.morphemes)}")
                        for m in morph.morphemes:
                            print(f"        • {m.type.value}: '{m.value}' ({m.meaning or 'no gloss'})")
                        if morph.features:
                            print(f"    → Features: {morph.features}")
        except Exception as e:
            if self.debug:
                print(f"\n  ❌ SEMANTIC ANALYSIS ERROR: {e}")
                import traceback
                traceback.print_exc()
            raise

        # Phase 4: Generate output
        if self.debug:
          print("\n" + "-" * 70)
          print("PHASE 4: CODE GENERATION (BYTECODE)")
          print("-" * 70)

        codegen = CodeGenerator()
        bytecode = codegen.generate(ast)

        if self.debug:
            print("Generated bytecode:")
            for i, instr in enumerate(bytecode):
                operand = f" {instr.operand}" if instr.operand is not None else ""
                print(f"  {i:02d}: {instr.opcode.value}{operand}")

        # Phase 5: VM EXECUTION
        codegen = CodeGenerator()
        bytecode = codegen.generate(ast)

        vm = StackVM(bytecode)

        if self.debug:
            print("\n" + "-" * 70)
            print("PHASE 5: VIRTUAL MACHINE EXECUTION")
            print("-" * 70)

        vm.run(debug=self.debug)

        latin_text = ast.value

        english_words = []
        for word_info in semantic_results['words']:
            english_words.append(word_info['meaning'])
        english_text = ' '.join(english_words)



        if self.debug:
            print(f"\n  Latin output:   {latin_text}")
            print(f"  English output: {english_text}")
            print("\n" + "="*70)
            print("COMPILATION COMPLETE")
            print("="*70 + "\n")

        result = {
            'javanese': javanese_text,
            'latin': latin_text,
            'english': english_text,
            'errors': reporter.errors,
        }

        if show_analysis:
            result['analysis'] = semantic_results
            result['ast'] = ast
            if self.debug and tokens:
                result['tokens'] = tokens

        return result

    def _print_ast(self, node: ASTNode, indent: int = 0):
        """Helper function to recursively print AST structure"""
        prefix = " " * indent
        if node.children:
            print(f"{prefix}{node.node_type.value} ('{node.value[:30]}{'...' if len(node.value) > 30 else ''}')")
            for child in node.children:
                self._print_ast(child, indent + 2)
        else:
            print(f"{prefix}{node.node_type.value}: '{node.value}'")

    def print_ast_pretty(self, node: ASTNode, prefix: str = "", is_last: bool = True):
        connector = "└── " if is_last else "├── "

        # Build node label
        label = node.node_type.value
        if node.value != "":
            # show value, but truncate if too long
            shown = node.value.replace("\n", "\\n")
            if len(shown) > 60:
                shown = shown[:60] + "..."
            label += f" ('{shown}')"

        print(prefix + connector + label)

        # Prepare prefix for children
        child_prefix = prefix + ("    " if is_last else "│   ")

        # Print children
        for i, child in enumerate(node.children):
            last_child = (i == len(node.children) - 1)
            self.print_ast_pretty(child, child_prefix, last_child)

# =============================================================================
# PHASE 5: BYTECODE + VM DEFINITIONS
# =============================================================================

class OpCode(Enum):
    PUSH  = "PUSH"
    PRINT = "PRINT"
    HALT  = "HALT"

@dataclass
class Instruction:
    opcode: OpCode
    operand: Optional[str] = None

class StackVM:
    """
    Simple stack-based virtual machine
    Runnable in Jupyter / Colab
    """

    def __init__(self, instructions: List[Instruction]):
        self.instructions = instructions
        self.stack = []
        self.ip = 0  # instruction pointer

    def run(self, debug: bool = False):
        while self.ip < len(self.instructions):
            instr = self.instructions[self.ip]

            if debug:
                print(f"[VM] IP={self.ip} | {instr} | STACK={self.stack}")

            if instr.opcode == OpCode.PUSH:
                self.stack.append(instr.operand)

            elif instr.opcode == OpCode.PRINT:
                value = self.stack.pop()
                print(value)

            elif instr.opcode == OpCode.HALT:
                break

            self.ip += 1
class CodeGenerator:
    """
    Converts AST into VM bytecode
    """

    def __init__(self):
        self.code: List[Instruction] = []

    def emit(self, opcode: OpCode, operand=None):
        self.code.append(Instruction(opcode, operand))

    def generate_word(self, word_node: ASTNode):
        # Push the word's latin value, then print it
        self.emit(OpCode.PUSH, word_node.value)
        self.emit(OpCode.PRINT)

    def generate(self, ast: ASTNode) -> List[Instruction]:
        for child in ast.children:
            if child.node_type == ASTNodeType.SENTENCE:
                for node in child.children:
                    if node.node_type == ASTNodeType.WORD:
                        self.generate_word(node)

        self.emit(OpCode.HALT)
        return self.code


#=============================================================================
# MAIN INTERFACE
#=============================================================================

def main():
    """Main command-line interface"""
    print("=" * 70)
    print("JAVANESE SCRIPT TRANSLATOR")
    print("=" * 70)
    print()

    # Check for debug mode argument
    import sys
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv

    if debug_mode:
        print("🔍 DEBUG MODE ENABLED")
        print()

    translator = Translator(debug=debug_mode)

    # Example texts
    examples = [
        "ꦲꦏꦸ ꦩꦔꦤ꧀ ꦱꦼꦒ",  # aku mangan sega (I eat rice)
        "ꦢꦺꦮꦺꦏꦺ ꦩ꧀ꦭꦏꦸ",  # dheweke mlaku (he/she walks)
        "ꦱꦸꦒꦺꦁ ꦄꦮꦤ꧀",  # sugeng awan (good day)
    ]

    print("Example translations:")
    print("-" * 70)

    for i, example in enumerate(examples, 1):
        print(f"\nExample {i}:")
        result = translator.translate(example, show_analysis=True)

        print(f"  Javanese:  {result['javanese']}")
        print(f"  Latin:     {result['latin']}")
        print(f"  English:   {result['english']}")

        if not debug_mode and 'analysis' in result:
            print(f"\n  Word Analysis:")
            for word_info in result['analysis']['words']:
                print(f"    - {word_info['word']}: {word_info['meaning']} ({word_info['pos']})")
                if word_info['morphology'] and word_info['morphology'].morphemes:
                    print(f"      Morphemes: {[f'{m.type.value}:{m.value}' for m in word_info['morphology'].morphemes]}")

    print("\n" + "=" * 70)
    print("\nInteractive Mode:")
    print("Commands:")
    print("  <text>     - Translate Javanese text")
    print("  debug on   - Enable debug mode")
    print("  debug off  - Disable debug mode")
    print("  quit       - Exit program")
    print("=" * 70)

    while True:
        try:
            text = input("\nJavanese> ").strip()

            if text.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if text.lower() == 'debug on':
                debug_mode = True
                translator.debug = True
                print("🔍 Debug mode enabled")
                continue

            if text.lower() == 'debug off':
                debug_mode = False
                translator.debug = False
                print("Debug mode disabled")
                continue

            if not text:
                continue

            result = translator.translate(text, show_analysis=True)

            if not debug_mode:
                print(f"\n  Latin:   {result['latin']}")
                print(f"  English: {result['english']}")

                if result['analysis']['words']:
                    print(f"\n  Analysis:")
                    for word_info in result['analysis']['words']:
                        status = "✓" if word_info['in_dictionary'] else "?"
                        print(f"    {status} {word_info['word']}: {word_info['meaning']} ({word_info['pos']})")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            if debug_mode:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()