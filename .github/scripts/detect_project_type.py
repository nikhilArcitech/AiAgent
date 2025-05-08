#!/usr/bin/env python3
# .github/scripts/detect_project_type.py

import os
import json
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_file_exists(file_path):
    """Check if a file exists in the repository"""
    return os.path.exists(file_path)

def get_file_content(file_path):
    """Get content of a file if it exists"""
    if not check_file_exists(file_path):
        return None
    
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        logger.warning(f"Couldn't read {file_path}: {e}")
        return None

def detect_project_type():
    """Detect the type of project in the repository"""
    # Dictionary to store all detected information
    project_info = {
        'PROJECT_TYPE': 'unknown',
        'BUILD_COMMAND': '',
        'TEST_COMMAND': '',
    }
    
    # Node.js detection
    if check_file_exists('package.json'):
        project_info['PROJECT_TYPE'] = 'nodejs'
        
        # Read package.json
        try:
            with open('package.json', 'r') as f:
                package_data = json.load(f)
                
            # Get Node.js version if specified
            if 'engines' in package_data and 'node' in package_data['engines']:
                project_info['NODE_VERSION'] = package_data['engines']['node'].replace('^', '').replace('~', '')
                
            # Detect package manager
            if check_file_exists('yarn.lock'):
                project_info['PACKAGE_MANAGER'] = 'yarn'
                project_info['INSTALL_COMMAND'] = 'yarn install'
            elif check_file_exists('pnpm-lock.yaml'):
                project_info['PACKAGE_MANAGER'] = 'pnpm'
                project_info['INSTALL_COMMAND'] = 'pnpm install'
            else:
                project_info['PACKAGE_MANAGER'] = 'npm'
                project_info['INSTALL_COMMAND'] = 'npm ci'
            
            # Get build and test commands from scripts
            if 'scripts' in package_data:
                scripts = package_data['scripts']
                
                # Try to find build command
                build_candidates = ['build', 'compile', 'dist', 'webpack', 'rollup']
                for cmd in build_candidates:
                    if cmd in scripts:
                        project_info['BUILD_COMMAND'] = f"{project_info['PACKAGE_MANAGER']} run {cmd}"
                        break
                
                # Try to find test command
                test_candidates = ['test', 'jest', 'mocha', 'vitest']
                for cmd in test_candidates:
                    if cmd in scripts:
                        project_info['TEST_COMMAND'] = f"{project_info['PACKAGE_MANAGER']} run {cmd}"
                        break
            
            # Set defaults if not found
            if not project_info['BUILD_COMMAND']:
                project_info['BUILD_COMMAND'] = f"{project_info['PACKAGE_MANAGER']} run build"
            
            if not project_info['TEST_COMMAND']:
                project_info['TEST_COMMAND'] = f"{project_info['PACKAGE_MANAGER']} test"
                
            # Check if it's a React project
            if ('dependencies' in package_data and 'react' in package_data['dependencies']) or \
               ('devDependencies' in package_data and 'react' in package_data['devDependencies']):
                project_info['FRAMEWORK'] = 'react'
            
            # Check if it's a Vue project
            if ('dependencies' in package_data and 'vue' in package_data['dependencies']) or \
               ('devDependencies' in package_data and 'vue' in package_data['devDependencies']):
                project_info['FRAMEWORK'] = 'vue'
                
            # Check if it's an Angular project
            if ('dependencies' in package_data and '@angular/core' in package_data['dependencies']) or \
               ('devDependencies' in package_data and '@angular/core' in package_data['devDependencies']):
                project_info['FRAMEWORK'] = 'angular'
                
        except Exception as e:
            logger.warning(f"Error parsing package.json: {e}")
    
    # Python detection
    elif check_file_exists('requirements.txt') or check_file_exists('setup.py') or check_file_exists('pyproject.toml'):
        project_info['PROJECT_TYPE'] = 'python'
        
        # Default commands
        project_info['INSTALL_COMMAND'] = 'pip install -r requirements.txt'
        project_info['BUILD_COMMAND'] = 'python -m build'
        project_info['TEST_COMMAND'] = 'pytest'
        
        # Check for poetry
        if check_file_exists('poetry.lock') or check_file_exists('pyproject.toml'):
            content = get_file_content('pyproject.toml')
            if content and 'tool.poetry' in content:
                project_info['PACKAGE_MANAGER'] = 'poetry'
                project_info['INSTALL_COMMAND'] = 'poetry install'
                project_info['BUILD_COMMAND'] = 'poetry build'
                project_info['TEST_COMMAND'] = 'poetry run pytest'
        
        # Check for pipenv
        if check_file_exists('Pipfile'):
            project_info['PACKAGE_MANAGER'] = 'pipenv'
            project_info['INSTALL_COMMAND'] = 'pipenv install --dev'
            project_info['TEST_COMMAND'] = 'pipenv run pytest'
            
        # Find Python version
        try:
            # Try to get from runtime.txt (common in some deployments)
            if check_file_exists('runtime.txt'):
                with open('runtime.txt', 'r') as f:
                    runtime = f.read().strip()
                    if runtime.startswith('python-'):
                        project_info['PYTHON_VERSION'] = runtime.replace('python-', '')
            
            # Try to get from pyproject.toml
            elif check_file_exists('pyproject.toml'):
                content = get_file_content('pyproject.toml')
                if content:
                    import re
                    # Try to match Python version specification
                    match = re.search(r'requires-python\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if match:
                        # Just take the first version number for simplicity
                        version_spec = match.group(1)
                        # Extract first version number (e.g. from >=3.7,<4.0)
                        version_match = re.search(r'(\d+\.\d+)', version_spec)
                        if version_match:
                            project_info['PYTHON_VERSION'] = version_match.group(1)
        except Exception as e:
            logger.warning(f"Error detecting Python version: {e}")
    
    # Java with Maven detection
    elif check_file_exists('pom.xml'):
        project_info['PROJECT_TYPE'] = 'maven'
        project_info['INSTALL_COMMAND'] = 'mvn clean install -DskipTests'
        project_info['BUILD_COMMAND'] = 'mvn package'
        project_info['TEST_COMMAND'] = 'mvn test'
        
        # Try to find Java version from pom.xml
        try:
            content = get_file_content('pom.xml')
            if content:
                import re
                match = re.search(r'<java.version>(\d+)</java.version>', content)
                if match:
                    project_info['JAVA_VERSION'] = match.group(1)
                else:
                    # Try another common format
                    match = re.search(r'<maven.compiler.source>(\d+)</maven.compiler.source>', content)
                    if match:
                        project_info['JAVA_VERSION'] = match.group(1)
        except Exception as e:
            logger.warning(f"Error parsing pom.xml: {e}")
    
    # Java with Gradle detection
    elif check_file_exists('build.gradle') or check_file_exists('build.gradle.kts'):
        project_info['PROJECT_TYPE'] = 'gradle'
        project_info['INSTALL_COMMAND'] = './gradlew dependencies'
        project_info['BUILD_COMMAND'] = './gradlew build -x test'
        project_info['TEST_COMMAND'] = './gradlew test'
        
        # Try to find Java version from build.gradle
        file_path = 'build.gradle' if check_file_exists('build.gradle') else 'build.gradle.kts'
        try:
            content = get_file_content(file_path)
            if content:
                import re
                match = re.search(r'sourceCompatibility\s*=\s*[\'"]?(\d+)[\'"]?', content)
                if match:
                    project_info['JAVA_VERSION'] = match.group(1)
        except Exception as e:
            logger.warning(f"Error parsing build.gradle: {e}")
            
        # Make gradlew executable
        if check_file_exists('./gradlew'):
            subprocess.run(['chmod', '+x', './gradlew'])
    
    # .NET detection
    elif any(check_file_exists(f) for f in ['*.csproj', '*.fsproj', '*.sln']):
        project_info['PROJECT_TYPE'] = 'dotnet'
        project_info['INSTALL_COMMAND'] = 'dotnet restore'
        project_info['BUILD_COMMAND'] = 'dotnet build --configuration Release'
        project_info['TEST_COMMAND'] = 'dotnet test'
        
        # Try to find .NET version
        for file in os.listdir():
            if file.endswith('.csproj') or file.endswith('.fsproj'):
                try:
                    content = get_file_content(file)
                    if content:
                        import re
                        match = re.search(r'<TargetFramework>net(\d+\.\d+)</TargetFramework>', content)
                        if match:
                            project_info['DOTNET_VERSION'] = match.group(1)
                except Exception as e:
                    logger.warning(f"Error parsing project file: {e}")
                break
    
    # Go detection
    elif check_file_exists('go.mod'):
        project_info['PROJECT_TYPE'] = 'go'
        project_info['INSTALL_COMMAND'] = 'go mod download'
        project_info['BUILD_COMMAND'] = 'go build ./...'
        project_info['TEST_COMMAND'] = 'go test ./...'
        
        # Try to find Go version
        try:
            content = get_file_content('go.mod')
            if content:
                import re
                match = re.search(r'^go\s+(\d+\.\d+)', content, re.MULTILINE)
                if match:
                    project_info['GO_VERSION'] = match.group(1)
        except Exception as e:
            logger.warning(f"Error parsing go.mod: {e}")
    
    # Ruby detection
    elif check_file_exists('Gemfile'):
        project_info['PROJECT_TYPE'] = 'ruby'
        project_info['INSTALL_COMMAND'] = 'bundle install'
        project_info['BUILD_COMMAND'] = 'bundle exec rake build' if check_file_exists('Rakefile') else 'echo "No build command found"'
        project_info['TEST_COMMAND'] = 'bundle exec rspec' if check_file_exists('spec') else 'bundle exec rake test' if check_file_exists('Rakefile') else 'echo "No test command found"'
        
        # Try to find Ruby version
        try:
            # From .ruby-version file
            if check_file_exists('.ruby-version'):
                content = get_file_content('.ruby-version')
                if content:
                    project_info['RUBY_VERSION'] = content.strip()
            
            # From Gemfile
            else:
                content = get_file_content('Gemfile')
                if content:
                    import re
                    match = re.search(r'^ruby\s+[\'"](\d+\.\d+\.\d+)[\'"]', content, re.MULTILINE)
                    if match:
                        project_info['RUBY_VERSION'] = match.group(1)
        except Exception as e:
            logger.warning(f"Error detecting Ruby version: {e}")
    
    # PHP detection
    elif check_file_exists('composer.json'):
        project_info['PROJECT_TYPE'] = 'php'
        project_info['INSTALL_COMMAND'] = 'composer install'
        project_info['BUILD_COMMAND'] = 'composer dump-autoload -o'
        
        # Check for PHPUnit
        if check_file_exists('phpunit.xml') or check_file_exists('phpunit.xml.dist'):
            project_info['TEST_COMMAND'] = './vendor/bin/phpunit'
        else:
            project_info['TEST_COMMAND'] = 'composer test' 
        
        # Try to find PHP version
        try:
            content = get_file_content('composer.json')
            if content:
                composer_data = json.loads(content)
                if 'require' in composer_data and 'php' in composer_data['require']:
                    # Extract version number from requirement like ">=7.4"
                    import re
                    version_str = composer_data['require']['php']
                    match = re.search(r'(\d+\.\d+)', version_str)
                    if match:
                        project_info['PHP_VERSION'] = match.group(1)
        except Exception as e:
            logger.warning(f"Error parsing composer.json: {e}")
    
    # Rust detection
    elif check_file_exists('Cargo.toml'):
        project_info['PROJECT_TYPE'] = 'rust'
        project_info['INSTALL_COMMAND'] = 'cargo fetch'
        project_info['BUILD_COMMAND'] = 'cargo build --release'
        project_info['TEST_COMMAND'] = 'cargo test'
        
        # Default to stable Rust
        project_info['RUST_VERSION'] = 'stable'
        
        # Try to find Rust version from rust-toolchain file
        if check_file_exists('rust-toolchain'):
            content = get_file_content('rust-toolchain')
            if content:
                project_info['RUST_VERSION'] = content.strip()
    
    # Docker projects
    if check_file_exists('Dockerfile') or check_file_exists('docker-compose.yml'):
        project_info['HAS_DOCKER'] = 'true'
        
        # If only Docker is detected with no other project type
        if project_info['PROJECT_TYPE'] == 'unknown':
            project_info['PROJECT_TYPE'] = 'docker'
            project_info['BUILD_COMMAND'] = 'docker build -t project:latest .'
            
            if check_file_exists('docker-compose.yml'):
                project_info['INSTALL_COMMAND'] = 'docker-compose pull'
                project_info['BUILD_COMMAND'] = 'docker-compose build'
                project_info['TEST_COMMAND'] = 'docker-compose up -d && docker-compose run tests'
    
    # Additional project type detection can be added here
    
    logger.info(f"Detected project type: {project_info['PROJECT_TYPE']}")
    
    # Set default for unknown project type
    if project_info['PROJECT_TYPE'] == 'unknown':
        project_info['INSTALL_COMMAND'] = 'echo "No install command detected"'
        project_info['BUILD_COMMAND'] = 'echo "No build command detected"'
        project_info['TEST_COMMAND'] = 'echo "No test command detected"'
    
    return project_info

def write_env_file(project_info):
    """Write detected information to environment file"""
    with open('project-type.env', 'w') as f:
        for key, value in project_info.items():
            f.write(f"{key}={value}\n")

if __name__ == "__main__":
    project_info = detect_project_type()
    write_env_file(project_info)
    
    # Print detected project type
    print(f"Detected project type: {project_info['PROJECT_TYPE']}")
    print(f"Build command: {project_info['BUILD_COMMAND']}")