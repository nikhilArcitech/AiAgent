#!/usr/bin/env python3
# .github/scripts/install_dependencies.py

import os
import sys
import json
import logging
import subprocess
import shlex

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, shell=False):
    """Run a shell command and return output"""
    logger.info(f"Running command: {command}")
    
    try:
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
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr

def install_dependencies():
    """Install dependencies based on detected project type"""
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
    install_command = project_info.get('INSTALL_COMMAND', '')
    
    logger.info(f"Installing dependencies for {project_type} project")
    
    # Run the install command if available
    if install_command and install_command != 'echo "No install command detected"':
        success, output = run_command(install_command, shell=True)
        if not success:
            logger.warning("Standard install command failed, trying fallback methods")
            
            # Fallback install methods based on project type
            if project_type == 'nodejs':
                package_manager = project_info.get('PACKAGE_MANAGER', 'npm')
                if package_manager == 'yarn':
                    run_command('yarn install --frozen-lockfile')
                elif package_manager == 'pnpm':
                    run_command('pnpm install --frozen-lockfile')
                else:
                    run_command('npm ci')
            
            elif project_type == 'python':
                if os.path.exists('requirements.txt'):
                    run_command('pip install -r requirements.txt')
                elif os.path.exists('setup.py'):
                    run_command('pip install -e .')
                elif os.path.exists('pyproject.toml'):
                    run_command('pip install -e .')
            
            elif project_type == 'maven':
                run_command('mvn dependency:resolve')
            
            elif project_type == 'gradle':
                if os.path.exists('./gradlew'):
                    run_command('chmod +x ./gradlew')
                    run_command('./gradlew --refresh-dependencies')
                else:
                    run_command('gradle --refresh-dependencies')
            
            elif project_type == 'dotnet':
                run_command('dotnet restore')
            
            elif project_type == 'go':
                run_command('go mod download')
            
            elif project_type == 'ruby':
                run_command('bundle install')
            
            elif project_type == 'php':
                run_command('composer install --no-scripts')
            
            elif project_type == 'rust':
                run_command('cargo fetch')
    else:
        logger.warning("No install command provided, attempting to detect dependencies automatically")
        
        # Try to guess install commands based on common files
        if os.path.exists('package.json'):
            if os.path.exists('yarn.lock'):
                run_command('yarn install')
            elif os.path.exists('pnpm-lock.yaml'):
                run_command('pnpm install')
            else:
                run_command('npm install')
        
        elif os.path.exists('requirements.txt'):
            run_command('pip install -r requirements.txt')
        
        elif os.path.exists('pom.xml'):
            run_command('mvn dependency:resolve')
        
        elif os.path.exists('build.gradle') or os.path.exists('build.gradle.kts'):
            if os.path.exists('./gradlew'):
                run_command('chmod +x ./gradlew')
                run_command('./gradlew dependencies')
            else:
                run_command('gradle dependencies')
        
        elif os.path.exists('Gemfile'):
            run_command('bundle install')
        
        elif os.path.exists('composer.json'):
            run_command('composer install')
        
        elif os.path.exists('Cargo.toml'):
            run_command('cargo fetch')
        
        else:
            logger.warning("Couldn't determine how to install dependencies automatically")
    
    logger.info("Dependency installation completed")

if __name__ == "__main__":
    install_dependencies()