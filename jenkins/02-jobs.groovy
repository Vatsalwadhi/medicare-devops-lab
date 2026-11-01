// Creates the three lab pipeline jobs (Pipeline script from SCM -> GitHub repo)
import jenkins.model.*
import hudson.plugins.git.*
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import com.cloudbees.jenkins.GitHubPushTrigger

def j = Jenkins.get()
def repo = 'https://github.com/Vatsalwadhi/medicare-devops-lab.git'
def jobs = [
  ['medicare-cicd-k8s',   'Jenkinsfile',           'Experiment 1: CI/CD pipeline - build, test, Dockerize and deploy MediCare+ to Kubernetes', true],
  ['medicare-blue-green', 'Jenkinsfile.bluegreen', 'Experiment 2: Automated blue-green deployment of MediCare+ on Kubernetes', false],
  ['medicare-devsecops',  'Jenkinsfile.devsecops', 'Experiment 3: DevSecOps pipeline for the MediCare+ healthcare system', false],
]
jobs.each { name, path, desc, webhook ->
  if (j.getItem(name) == null) {
    def job = j.createProject(WorkflowJob, name)
    def scm = new GitSCM(GitSCM.createRepoList(repo, null), [new BranchSpec('*/main')], null, null, [])
    def flow = new CpsScmFlowDefinition(scm, path)
    flow.setLightweight(true)
    job.setDefinition(flow)
    job.setDescription(desc)
    if (webhook) { job.addTrigger(new GitHubPushTrigger()) }
    job.save()
    println "MediCare lab: created job ${name}"
  }
}
