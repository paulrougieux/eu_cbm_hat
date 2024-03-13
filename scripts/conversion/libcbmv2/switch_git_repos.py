"""The purpose of this script is to switch git repositories from version 1 to
version 2 of libcbm


Switch to v1 or v2:

    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 1

    ipython ~/eu_cbm/eu_cbm_hat/scripts/conversion/libcbmv2/switch_git_repos.py -- --version 2

"""

import argparse
import git
import sys
from eu_cbm_hat import eu_cbm_aidb_dir


parser = argparse.ArgumentParser(description='Switch git repositories for libcbm dependencies')
parser.add_argument('--version', type=str, help='Name of the version')
args = parser.parse_args()
LIBCBM_VERSION = str(args.version)


def find_sys_path(path_contains:str):
    """Find path that contains the given characters. Raise an error if there's
    not exactly one matching path. Find location of git repositories for
    libcbm_py and eu_cbm_hat
    """
    matching_paths = [path for path in sys.path if path_contains in path]
    # Exclude the path of the current script
    matching_paths = [p for p in matching_paths if "scripts" not in p]
    if len(matching_paths) != 1:
        msg = f"Expected one path containing {path_contains}, "
        msg += f"found {len(matching_paths)}\n"
        msg += f"{matching_paths}"
        raise ValueError(msg)
    return matching_paths[0]


def checkout_branch(git_repo: git.repo.base.Repo, branch_name:str):
    """Check if a repository has any changes and checkout the given branch
    """
    if git_repo.is_dirty(untracked_files=True):
        msg = f"There are changes in {git_repo}.\n"
        msg += f"Not checking out the '{branch_name}' branch."
        raise RuntimeError(msg)
    git_repo.git.checkout(branch_name)
    print(f"Checked out branch: {branch_name} of {git_repo}.")


repo_eu_cbm_hat = git.Repo(find_sys_path("eu_cbm_hat"))
repo_eu_cbm_aidb = git.Repo(eu_cbm_aidb_dir)
repo_libcbm_py = git.Repo(find_sys_path("libcbm_py"))

if LIBCBM_VERSION == "1":
    checkout_branch(repo_libcbm_py, "1.x")
    checkout_branch(repo_eu_cbm_hat, "main")
    checkout_branch(repo_eu_cbm_aidb, "main")
    assert repo_libcbm_py.active_branch.name == '1.x'
    assert repo_eu_cbm_hat.active_branch.name == 'main'

elif LIBCBM_VERSION == "2":
    checkout_branch(repo_libcbm_py, "2.x")
    checkout_branch(repo_eu_cbm_hat, "libcbm2")
    checkout_branch(repo_eu_cbm_aidb, "libcbm2")
    assert repo_libcbm_py.active_branch.name == '2.x'
    assert repo_eu_cbm_hat.active_branch.name == 'libcbm2'

else:
    raise ValueError(f"Libcbm version {LIBCBM_VERSION} not recognised")
