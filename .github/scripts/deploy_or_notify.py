# .github/scripts/deploy_or_notify.py
import os
import sys
import json
import subprocess
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration - using environment variables set from credentials.env
AUTO_DEPLOY = os.environ.get("AUTO_DEPLOY", "false").lower() == "true"
DEPLOY_ENVIRONMENT = os.environ.get("DEPLOY_ENVIRONMENT", "staging")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USER")  # Updated to match workflow env variable
SMTP_PASSWORD = os.environ.get("SMTP_PASS")  # Updated to match workflow env variable
NOTIFICATION_EMAIL = os.environ.get("RECIPIENT_EMAIL")  # Updated to match workflow env variable
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "").split("/")[-1]
COMMIT_SHA = os.environ.get("GITHUB_SHA", "unknown")
GITHUB_WORKFLOW = os.environ.get("GITHUB_WORKFLOW", "AI Build Agent")

def send_notification(subject, message, is_html=False):
    """Send email notification"""
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, NOTIFICATION_EMAIL]):
        logger.warning("Email notification credentials not configured. Check credentials.env setup.")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USERNAME
        msg["To"] = NOTIFICATION_EMAIL
        
        if is_html:
            msg.attach(MIMEText(message, "html"))
        else:
            msg.attach(MIMEText(message, "plain"))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Notification email sent to {NOTIFICATION_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

def get_commit_info():
    """Get information about the commit that triggered the build"""
    try:
        commit_msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%s"], 
            text=True
        )
        author = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%an <%ae>"], 
            text=True
        )
        return commit_msg, author
    except Exception as e:
        logger.error(f"Error getting commit info: {e}")
        return "Unknown commit message", "Unknown author"

def deploy_to_environment():
    """Deploy the build to the specified environment"""
    try:
        # This would be adapted to your specific deployment system
        # Example: Deploy to a server via SSH, or trigger a cloud deployment
        logger.info(f"Deploying to {DEPLOY_ENVIRONMENT} environment")
        
        # Simulate a deployment process
        logger.info("Preparing deployment package...")
        subprocess.run(["mkdir", "-p", "deploy"])
        subprocess.run(["cp", "-r", "dist", "deploy/"])
        
        logger.info("Running deployment script...")
        # This would be your actual deployment command
        # For example: subprocess.run(["aws", "s3", "sync", "dist/", f"s3://my-bucket/{DEPLOY_ENVIRONMENT}/"])
        
        logger.info(f"Successfully deployed to {DEPLOY_ENVIRONMENT}")
        return True
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return False

def main():
    # Log the environment variables being used (without exposing secrets)
    logger.info(f"Using SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
    logger.info(f"Using notification email: {NOTIFICATION_EMAIL}")
    logger.info(f"Auto deploy enabled: {AUTO_DEPLOY}")
    logger.info(f"Deploy environment: {DEPLOY_ENVIRONMENT}")
    
    # Get commit information
    commit_msg, author = get_commit_info()
    short_sha = COMMIT_SHA[:7] if len(COMMIT_SHA) >= 7 else COMMIT_SHA
    
    # Handle auto-deployment if enabled
    if AUTO_DEPLOY:
        deploy_success = deploy_to_environment()
        
        if deploy_success:
            subject = f"[{REPO_NAME}] Successfully Built and Deployed to {DEPLOY_ENVIRONMENT}"
            message = f"""
            Build and deployment successful!
            
            Repository: {REPO_NAME}
            Environment: {DEPLOY_ENVIRONMENT}
            Commit: {short_sha} - {commit_msg}
            Author: {author}
            Workflow: {GITHUB_WORKFLOW}
            
            The build has been automatically deployed to the {DEPLOY_ENVIRONMENT} environment.
            """
            send_notification(subject, message)
            logger.info(f"Build deployed to {DEPLOY_ENVIRONMENT}")
        else:
            subject = f"[{REPO_NAME}] Build Successful but Deployment Failed"
            message = f"""
            The build was successful, but automatic deployment failed.
            
            Repository: {REPO_NAME}
            Environment: {DEPLOY_ENVIRONMENT}
            Commit: {short_sha} - {commit_msg}
            Author: {author}
            Workflow: {GITHUB_WORKFLOW}
            
            Please check the logs and deploy manually.
            """
            send_notification(subject, message)
            logger.warning("Deployment failed")
            sys.exit(1)
    else:
        # Just notify that build is ready for deployment
        subject = f"[{REPO_NAME}] Build Successful - Ready for Deployment"
        message = f"""
        The build was successful and is ready for deployment.
        
        Repository: {REPO_NAME}
        Commit: {short_sha} - {commit_msg}
        Author: {author}
        Workflow: {GITHUB_WORKFLOW}
        
        You can deploy this build manually to your desired environment.
        """
        send_notification(subject, message)
        logger.info("Build successful, notification sent")

if __name__ == "__main__":
    main()