#!/usr/bin/env python3
import re
import os
import sys
import json
import subprocess
from pathlib import Path
from openai import OpenAI

class BuildErrorHandler:
    def __init__(self):
        self.project_type = os.getenv('PROJECT_TYPE', '')
        self.max_error_length = int(os.getenv('MAX_ERROR_LENGTH', 10000))
        
        # Initialize OpenAI client using the OPENAI_API_KEY from credentials.env
        self.openai_client = None
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            print(f"OpenAI client initialized with API key {'*' * 5}{openai_api_key[-4:] if openai_api_key else ''}")
        else:
            print("WARNING: No OpenAI API key found in environment variables. AI analysis will be skipped.")

    def analyze_error(self):
        """Main analysis entry point that determines error type and suggests fixes"""
        if not os.path.exists('build_log.txt'):
            print("No build log found")
            return 'major', []

        # Try AI analysis first if available
        if self.openai_client:
            error_type, fixes = self._analyze_with_ai()
            if error_type:
                return error_type, fixes

        # Fall back to traditional analysis
        return self._analyze_traditional()

    def fix_errors(self, error_type):
        """Main fixing entry point that applies fixes based on error type"""
        if error_type != 'minor':
            return False

        return self._apply_fixes()

    def _analyze_with_ai(self):
        """Use OpenAI API to analyze build errors"""
        try:
            with open('build_log.txt', 'r') as file:
                error_text = file.read()[:self.max_error_length]

            print("Analyzing errors with AI...")
            response = self.openai_client.chat.completions.create(
                model=os.getenv('AI_MODEL', 'gpt-4-turbo-preview'),
                messages=[{
                    "role": "system",
                    "content": f"""You are a {self.project_type} build error expert. Analyze these errors and:
                    1. Categorize as MINOR (fixable) or MAJOR (needs human)
                    2. For MINOR: Provide specific fixes in format:
                       FILE: <path>
                       LINE: <number>
                       FIX: <correction>
                    3. For MAJOR: Explain the core issue"""
                }, {
                    "role": "user",
                    "content": error_text
                }]
            )

            ai_analysis = response.choices[0].message.content
            error_type = 'minor' if 'MINOR' in ai_analysis else 'major'
            fixes = self._parse_ai_fixes(ai_analysis) if error_type == 'minor' else []

            # Save analysis results
            with open('ai_fixes.json', 'w') as file:
                json.dump({'error_type': error_type, 'analysis': ai_analysis, 'fixes': fixes}, file, indent=2)

            with open('error_type.txt', 'w') as file:
                file.write(error_type)

            print(f"AI analysis complete: {error_type} error")
            return error_type, fixes

        except Exception as e:
            print(f"AI analysis failed: {e}")
            return None, []

    def _parse_ai_fixes(self, analysis_text):
        """Extract fix suggestions from AI response"""
        fixes = []
        file_pattern = r'FILE:\s*([^\n]+)'
        line_pattern = r'LINE:\s*(\d+)'
        fix_pattern = r'FIX:\s*([^\n]+(?:\n(?!\s*(?:FILE|LINE)).*)*)'

        file_matches = re.finditer(file_pattern, analysis_text)
        line_matches = re.finditer(line_pattern, analysis_text)
        fix_matches = re.finditer(fix_pattern, analysis_text)

        files = [m.group(1).strip() for m in file_matches]
        lines = [int(m.group(1).strip()) for m in line_matches]
        fixes_text = [m.group(1).strip() for m in fix_matches]

        if len(files) == len(lines) == len(fixes_text):
            return [{'file': f, 'line': l, 'fix': fx} for f, l, fx in zip(files, lines, fixes_text)]
        return []

    def _analyze_traditional(self):
        """Fallback error analysis using pattern matching"""
        with open('build_log.txt', 'r') as file:
            build_log = file.read()

        error_type = 'major'
        patterns = {
            'whitespace': [r'indentation contains tabs', r'trailing whitespace'],
            'import': [r'cannot find module', r'ModuleNotFoundError'],
            'syntax': [r'SyntaxError', r'Missing semicolon'],
            'linting': [r'ESLint', r'pylint']
        }

        for category, pats in patterns.items():
            if any(re.search(p, build_log, re.IGNORECASE) for p in pats):
                error_type = 'minor'
                break

        # Project-specific checks
        if self.project_type == 'node' and re.search(r'npm ERR! missing script', build_log):
            error_type = 'minor'
        elif self.project_type == 'python' and re.search(r'IndentationError', build_log):
            error_type = 'minor'

        with open('error_type.txt', 'w') as file:
            file.write(error_type)

        print(f"Traditional analysis complete: {error_type} error")
        return error_type, []

    def _apply_fixes(self):
        """Apply all available fixes to the codebase"""
        applied_fixes = 0

        # 1. Apply AI-suggested fixes if available
        if os.path.exists('ai_fixes.json'):
            with open('ai_fixes.json', 'r') as file:
                data = json.load(file)
                fixes = data.get('fixes', [])
                
                for fix in fixes:
                    if self._apply_single_fix(fix.get('file'), fix.get('line'), fix.get('fix')):
                        applied_fixes += 1

        # 2. Apply automatic fixes for common issues
        error_details = self._extract_error_details()
        files_to_check = self._get_project_files()

        for file_path in files_to_check:
            if os.path.exists(file_path):
                self._fix_whitespace(file_path)
                self._fix_imports(file_path)
                applied_fixes += 1

        # 3. Project-specific fixes
        if self.project_type == 'node' and os.path.exists('package.json'):
            self._ensure_build_script()
        elif self.project_type == 'python' and not os.path.exists('tests'):
            os.makedirs('tests', exist_ok=True)
            with open('tests/__init__.py', 'w') as f:
                f.write('# Test initialization\n')

        print(f"Applied {applied_fixes} fixes")
        return applied_fixes > 0

    def _apply_single_fix(self, file_path, line_num, fix_content):
        """Apply a specific fix to a file"""
        if not file_path or not os.path.exists(file_path) or not line_num or not fix_content:
            return False

        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()

            if 1 <= line_num <= len(lines):
                lines[line_num - 1] = fix_content + '\n'
                with open(file_path, 'w') as file:
                    file.writelines(lines)
                return True
        except Exception as e:
            print(f"Error applying fix to {file_path}: {e}")
        return False

    def _extract_error_details(self):
        """Get error locations from build log"""
        details = []
        if not os.path.exists('build_log.txt'):
            return details

        with open('build_log.txt', 'r') as file:
            build_log = file.read()

        patterns = [
            r'([\w\/.-]+):(\d+)(?::(\d+))?: (.*)',
            r'File "([\w\/.-]+)", line (\d+)',
            r'at ([\w\/.-]+):(\d+)'
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, build_log):
                groups = match.groups()
                if len(groups) >= 2:
                    details.append({
                        'file': groups[0],
                        'line': int(groups[1]),
                        'message': groups[-1] if len(groups) > 2 else "Unknown error"
                    })
        return details

    def _get_project_files(self):
        """Get relevant files based on project type"""
        extensions = {
            'nodejs': ['js', 'jsx', 'ts', 'tsx'],  # Updated to match workflow PROJECT_TYPE
            'python': ['py'],
            'java': ['java'],
            'go': ['go'],
            'rust': ['rs'],
            'default': ['js', 'py', 'java', 'go', 'rs', 'ts', 'jsx', 'tsx']
        }

        exts = extensions.get(self.project_type, extensions['default'])
        files = []
        for ext in exts:
            files.extend(Path('.').glob(f'**/*.{ext}'))
        return [str(f) for f in files if 'node_modules' not in str(f)]

    def _fix_whitespace(self, file_path):
        """Fix common whitespace issues"""
        try:
            with open(file_path, 'r') as file:
                content = file.read()

            content = content.replace('\t', '    ')
            content = '\n'.join(line.rstrip() for line in content.splitlines())
            if not content.endswith('\n'):
                content += '\n'

            with open(file_path, 'w') as file:
                file.write(content)
        except Exception as e:
            print(f"Error fixing whitespace in {file_path}: {e}")

    def _fix_imports(self, file_path):
        """Fix import-related issues"""
        if not os.path.exists('build_log.txt'):
            return

        with open('build_log.txt', 'r') as file:
            build_log = file.read()

        if self.project_type == 'nodejs':  # Updated to match workflow PROJECT_TYPE
            self._fix_node_imports(build_log)
        elif self.project_type == 'python':
            self._fix_python_imports(build_log)

    def _fix_node_imports(self, build_log):
        """Handle Node.js import issues"""
        missing = re.findall(r'cannot find module [\'"]([^\'"]+)[\'"]', build_log, re.IGNORECASE)
        if not missing:
            return

        print(f"Installing missing npm modules: {', '.join(missing)}")
        subprocess.run(['npm', 'install', '--save'] + missing, check=False)

        if os.path.exists('package.json'):
            with open('package.json', 'r+') as file:
                data = json.load(file)
                data.setdefault('dependencies', {})
                for module in missing:
                    if module not in data['dependencies']:
                        data['dependencies'][module] = '*'
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()

    def _fix_python_imports(self, build_log):
        """Handle Python import issues"""
        missing = re.findall(r'No module named [\'"]([^\'"]+)[\'"]', build_log)
        missing += re.findall(r'ModuleNotFoundError: No module named [\'"]([^\'"]+)[\'"]', build_log)
        if not missing:
            return

        for module in {m.split('.')[0] for m in missing}:
            print(f"Installing missing Python module: {module}")
            subprocess.run(['pip', 'install', module], check=False)

        if os.path.exists('requirements.txt'):
            with open('requirements.txt', 'r+') as file:
                reqs = file.read().splitlines()
                for module in {m.split('.')[0] for m in missing}:
                    if not any(line.startswith(f"{module}==") or line == module for line in reqs):
                        reqs.append(module)
                file.seek(0)
                file.write('\n'.join(reqs) + '\n')
                file.truncate()

    def _ensure_build_script(self):
        """Ensure package.json has a build script"""
        with open('package.json', 'r+') as file:
            data = json.load(file)
            data.setdefault('scripts', {})
            if 'build' not in data['scripts']:
                data['scripts']['build'] = 'echo "No build script specified"'
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()

def main():
    handler = BuildErrorHandler()
    
    # Analyze errors
    error_type, _ = handler.analyze_error()
    
    # Fix errors if minor
    if error_type == 'minor':
        print("Attempting to fix minor errors...")
        if handler.fix_errors(error_type):
            print("Fixes applied. You should now rebuild the project.")
        else:
            print("No fixes could be automatically applied.")
    else:
        print("Major errors detected that require manual intervention.")

if __name__ == "__main__":
    main()