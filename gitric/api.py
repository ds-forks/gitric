from os import getcwd

from fabric.state import env
from fabric.colors import green
from fabric.contrib.files import exists
from fabric.context_managers import settings, lcd
from fabric.api import cd, run, puts, task, abort, local

cwd = getcwd()


@task
def allow_dirty():
    """
    allow pushing even when the working copy is dirty
    """
    env.gitric_allow_dirty = True


@task
def force_push():
    """
    allow pushing even when history will be lost
    """
    env.gitric_force_push = True


def git_init(repo_path):
    """
    create a git repository if necessary [remote]
    """

    # check if it is a git repository yet
    if exists('%s/.git' % repo_path):
        return

    puts(green('Creating new git repository ') + repo_path)

    # create repository folder if necessary
    run('mkdir -p %s' % repo_path, quiet=True)

    with cd(repo_path), settings(warn_only=True):
        # initialize the remote repository
        if run('git init').failed:
            run('git init-db')

        # silence git complaints about pushes coming in on the current branch
        # the pushes only seed the immutable object store and do not modify the
        # working copy
        run('git config receive.denyCurrentBranch ignore')


def git_seed(
         repo_path, commit=None, ignore_untracked_files=False, git_src=cwd):
    """
    seed a git repository (and create if necessary) [remote]
    """

    # check if the local repository is dirty
    dirty_working_copy = git_is_dirty(ignore_untracked_files, git_src)
    if dirty_working_copy:
        abort(
            'Working copy is dirty. This check can be overridden by\n'
            'importing gitric.api.allow_dirty and adding allow_dirty to your '
            'call.')

    # check if the remote repository exists and create it if necessary
    git_init(repo_path)

    # use specified commit or HEAD
    commit = commit or git_head_rev(git_src)

    # push the commit to the remote repository
    #
    # (note that pushing to the master branch will not change the contents
    # of the working directory)

    puts(green('Pushing commit ') + commit)

    with settings(warn_only=True):
        force = ('gitric_force_push' in env) and '-f' or ''
        with lcd(git_src):
            print(local("echo pwd"))
            push = local(
                'git push git+ssh://%s@%s:%s%s %s:refs/heads/master %s' % (
                    env.user, env.host, env.port, repo_path, commit, force))

    if push.failed:
        abort(
            '%s is a non-fast-forward\n'
            'push. The seed will abort so you don\'t lose information. '
            'If you are doing this\nintentionally import '
            'gitric.api.force_push and add it to your call.' % commit)


def git_reset(repo_path, commit=None, git_src=cwd):
    """
    reset the working directory to a specific commit [remote]
    """

    # use specified commit or HEAD
    commit = commit or git_head_rev(git_src)

    puts(green('Resetting to commit ') + commit)

    # reset the repository and working directory
    with cd(repo_path):
        run('git reset --hard %s' % commit)


def git_head_rev(git_src=cwd):
    """
    find the commit that is currently checked out [local]
    """
    with lcd(git_src):
        return local('git rev-parse HEAD', capture=True)


def git_is_dirty(ignore_untracked_files, git_src=cwd):
    """
    check if there are modifications in the repository [local]
    """

    if 'gitric_allow_dirty' in env:
        return False

    untracked_files = '--untracked-files=no' if ignore_untracked_files else ''
    with lcd(git_src):
        return local(
            'git status %s --porcelain' % untracked_files, capture=True) != ''
