import os
import subprocess
import re

#DEBUG = True
DEBUG = False
targetdir = 'unirepo'
baserepo = ('https://github.com/lwrage/osate2-core.git', 'core')
repos = [
    ('https://github.com/osate/osate2-plugins.git', 'analyses'),
    ('https://github.com/osate/osate-ge.git', 'ge'),
    ('https://github.com/osate/ErrorModelV2.git', 'emv2'),
    ('https://github.com/osate/alisa.git', 'alisa')
]
#baserepo = ('file:///home/lw/git/osate/osate2-core', 'core')
#repos = [
#    ('file:///home/lw/git/osate/osate2-plugins', 'analyses'),
#    ('file:///home/lw/git/osate/osate-ge', 'ge'),
#    ('file:///home/lw/git/osate/ErrorModelV2', 'emv2'),
#    ('file:///home/lw/git/osate/alisa', 'alisa')
#]
#baserepo = ('git@github.com:osate/sandbox', 'sandbox')
#baserepo = ('file:///home/lw/tmp/sandbox', 'sandbox')
#repos = [('git@github.com:osate/buildtest', 'buildtest')]

def splitRepo(repo):
    url = repo[0]
    subproject = url.split('/')[-1]
    if subproject.endswith('.git'):
        subproject = subproject[:-4]
    subdir = repo[1]
    return (url, subproject, subdir)
    
def git(cmd, ch=True):
    pattern = re.compile('  *')
    args = ['git'] + pattern.split(cmd)
    res = subprocess.run(args, stdout=subprocess.PIPE, check=ch)
    if DEBUG:
        print(res)
    return(res)

def gitCommit(params, msg):
    pattern = re.compile('  *')
    args = ['git', 'commit'] + pattern.split(params) + [msg]
    res = subprocess.run(args, stdout=subprocess.PIPE, check=True)
    if DEBUG:
        print(res)
    return(res)

def splitRef(line):
    columns = line.split('\t')
    branch = '/'.join(columns[1].split('/')[2:])
    ref = columns[0]
    return (branch, ref)
    
def commitMerge(project, branch):
    currentBranch=git('symbolic-ref HEAD').stdout.decode('utf-8')
    changes=git('status --porcelain').stdout != b''
    merging=git('merge HEAD', ch=False).returncode != 0
    if not(changes or merging):
        print('INFO: no commit required')
    else:
        print('INFO: committing')
        gitCommit('-m', '[Project] Merge branch {} of {} into {}'.format(branch, project, currentBranch))
    
def createBranches(subproject, subdir):
    print('INFO: create local branches for ' + subproject)
    res = git('ls-remote --heads ' + subproject)
    heads = res.stdout.decode('utf-8').split('\n')[0:-1]
    for head in heads:
        (branch, ref) = splitRef(head)
        subbranch = '{}/{}'.format(subproject, branch)
        print('INFO: create local branch for ' + subbranch)
        git('checkout --quiet -b {} branchroot'.format(subbranch))
        git('reset --quiet --hard')
        git('clean --quiet -d --force')
        print('INFO: merging ' + subbranch)
        git('merge --quiet --allow-unrelated-histories --no-commit remotes/' + subbranch)
        commitMerge(subproject, subbranch)
        moveFiles(subproject, subdir)

def createTags(subproject):
    print('INFO: create tags for ' + subproject)
    res = git('ls-remote --tags ' + subproject)
    tags = res.stdout.decode('utf-8').split('\n')[0:-1]
    for tag in tags:
        (tagname, ref) = splitRef(tag)
        if tagname.endswith('^{}'):
            newtag = tagname[:-3]
        else:
            newtag = tagname
        newtag = '{}/{}'.format(subproject, newtag)
        print('INFO: copy tag {} to {} for {}'.format(tagname, newtag, ref))  
        res = git('tag {} {}'.format(newtag, ref), ch=False)
        if res.returncode == 0:
            print('ok')
        else:
            print('failed')

def moveFiles(subproject, subdir):
    print('INFO: move files to subdirectory ' + subdir)
    os.mkdir(subdir)
    for f in os.listdir():
        if not f in [subdir, '.git']:
            # print(f)
            git('mv -k {} {}/'.format(f, subdir))
    gitCommit('-m', '[Project] Move {} files into sub directory {}'.format(subproject, subdir))

def mergeRepo(repo):
    (url, subproject, subdir) = splitRepo(repo)
    print('INFO: fetching ' + subproject)
    git('remote add {} {}'.format(subproject, url))
    git ('fetch --no-tags ' + subproject)
    createBranches(subproject, subdir)
    createTags(subproject) 

def mergeAll(branch):
    git ('checkout --quiet ' + branch)
    for repo in repos:
        (url, subproject, subdir) = splitRepo(repo)
        exists = git('show-branch refs/heads/{}/{}'.format(subproject, branch), ch=False).returncode == 0
        if exists:
            print('INFO: merge {}/{} into {}'.format(subproject, branch, branch))
            git('merge --quiet --allow-unrelated-histories --no-commit refs/heads/{}/{}'.format(subproject, branch))
            commitMerge(subproject, branch)
        else:
            print('????: no {} branch in {}'.format(branch, subproject)) 
        
def main():
    if os.path.exists(targetdir):
        print('target directory exists')
        return

    # clone osate2-core
    (url, project, subdir) = splitRepo(baserepo)
    print('INFO: Clone base repo ' + project)
    git('clone --no-tags --quiet {} {}'.format(url, targetdir))
    os.chdir(targetdir)
    git('checkout --orphan branchroot')
    git('reset --quiet --hard')
    git('clean --quiet -d --force')
    git('commit --allow-empty --allow-empty-message -m ""') 
    git('remote rename origin ' + project)
    res = git('ls-remote --heads ' + project)
    heads = res.stdout.decode('utf-8').split('\n')[0:-1]
    for head in heads:
        (branch, ref) = splitRef(head)
        print('INFO: on branch ' + branch)
        git('checkout --quiet ' + branch)
        moveFiles(project, subdir)
    createTags(project)
    for repo in repos:
        mergeRepo(repo)
    mergeAll('master')
    mergeAll('develop')
    
if __name__ == '__main__':
    # execute only if run as a script
    main()
