// Headless Jenkins setup: admin user (password from a root-only file), auth strategy, URL
import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState

def j = Jenkins.get()
def pw = new File('/var/lib/jenkins/secrets/admin_pw').text.trim()
def realm = new HudsonPrivateSecurityRealm(false)
realm.createAccount('admin', pw)
j.setSecurityRealm(realm)
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
j.setAuthorizationStrategy(strategy)
j.setNumExecutors(2)
j.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
JenkinsLocationConfiguration.get().setUrl('http://54.81.195.45:8080/')
j.save()
println 'MediCare lab: security configured'
