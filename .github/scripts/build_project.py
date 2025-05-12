#!/usr/bin/env python3
# .github/scripts/build_project.py

import os
import sys
import logging
import subprocess
import shlex

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, shell=False, output_file=None):
    """Run a shell command and return output"""
    logger.info(f"Running command: {command}")
    
    try:
        if output_file:
            with open(output_file, 'w') as f:
                if shell:
                    process = subprocess.run(command, shell=True, check=True, text=True, 
                                            stdout=f, stderr=subprocess.STDOUT)
                else:
                    process = subprocess.run(shlex.split(command), check=True, text=True,
                                            stdout=f, stderr=subprocess.STDOUT)
            return True, ""
        else:
            if shell:
                process = subprocess.run(command, shell=True, check=True, text=True, 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                process = subprocess.run(shlex.split(command), check=True, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            logger.info(f"Command output: {process.stdout}")
            return True, process.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        if output_file:
            logger.error(f"Error output saved to {output_file}")
            # Read the error output from the file to return it
            try:
                with open(output_file, 'r') as f:
                    error_output = f.read()
                return False, error_output
            except Exception as read_err:
                logger.error(f"Could not read error output: {read_err}")
                return False, f"Command failed with exit code {e.returncode}"
        else:
            logger.error(f"Error output: {e.stderr}")
            return False, e.stderr

def build_project():
    """Build the project based on detected project type"""
    # Load project type information
    project_info = {}
    try:
        with open('project-type.env', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    project_info[key] = value
    except Exception as e:
        logger.error(f"Error loading project type: {e}")
        sys.exit(1)
   
    project_type = project_info.get('PROJECT_TYPE', 'unknown')
    build_command = project_info.get('BUILD_COMMAND', '')
   
    logger.info(f"Building {project_type} project")
   
    # Create log file for build output
    log_file = 'build.log'
   
    # Run the build command if available
    if build_command and build_command != 'echo "No build command detected"':
        success, output = run_command(build_command, shell=True, output_file=log_file)
       
        if not success:
            logger.error("Build failed")
           
            # Save error for analysis
            # Check if output is None and provide a default value if it is
            error_content = output if output is not None else "No error details available"
            with open('build_errors.txt', 'w') as f:
                f.write(error_content)
           
            sys.exit(1)
        else:
            logger.info("Build succeeded")
    else:
        logger.warning("No build command available for this project type")
       
        # Try known build commands based on project type
        fallback_commands = {
            'nodejs': 'npm run build',
            'python': 'python -m build',
            'maven': 'mvn package',
            'gradle': './gradlew build',
            'dotnet': 'dotnet build',
            'go': 'go build ./...',
            'ruby': 'bundle exec rake build',
            'rust': 'cargo build --release',
            'php': 'composer install && composer build',
            'scala': 'sbt compile package',
            'docker': 'docker build -t project:latest .',
            'android': './gradlew assembleRelease',
            'ios': 'xcodebuild -project *.xcodeproj -scheme "Release" -configuration Release',
            'flutter': 'flutter build',
            'c': 'make',
            'cpp': 'make'
        }
        
        if project_type in fallback_commands:
            fallback_cmd = fallback_commands[project_type]
            logger.info(f"Trying fallback build command: {fallback_cmd}")
            
            success, output = run_command(fallback_cmd, shell=True, output_file=log_file)
            
            if not success:
                logger.error(f"Fallback build for {project_type} failed")
                
                # Check for common build requirements/dependencies
                if project_type == 'nodejs':
                    # Check if node_modules exists
                    if not os.path.exists('node_modules'):
                        logger.info("Running npm install first...")
                        run_command('npm install', shell=True, output_file='npm_install.log')
                        # Try build again
                        success, output = run_command(fallback_cmd, shell=True, output_file=log_file)
                elif project_type == 'python':
                    # Try installing requirements
                    if os.path.exists('requirements.txt'):
                        logger.info("Installing Python dependencies...")
                        run_command('pip install -r requirements.txt', shell=True, output_file='pip_install.log')
                        # Try build again
                        success, output = run_command(fallback_cmd, shell=True, output_file=log_file)
                
                if not success:
                    # Check if output is None and provide a default value if it is
                    error_content = output if output is not None else "No error details available"
                    with open('build_errors.txt', 'w') as f:
                        f.write(error_content)
                    sys.exit(1)
                else:
                    logger.info("Build succeeded after dependency installation")
            else:
                logger.info("Build succeeded with fallback command")
        else:
            logger.error(f"No fallback build command available for {project_type} project")
            with open('build_errors.txt', 'w') as f:
                f.write(f"Unknown project type: {project_type}\nNo build command available.")
            sys.exit(1)
    
    logger.info("Build process completed successfully")
    return True


if __name__ == "__main__":
    build_project()