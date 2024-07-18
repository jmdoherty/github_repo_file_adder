import requests
from requests.exceptions import HTTPError
import json
import argparse
import os
import re
import time
import base64

# Process arguments
parser = argparse.ArgumentParser(
    description="Add a file to a repository, either directly or thru pull requests",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--url",
    dest="url",
    default="https://api.github.com",
    help="URL of Github API endpoint",
)
parser.add_argument(
    "--repo",
    dest="repo",
    required=True,
    help="Repository to add file to in org/repo format",
)
parser.add_argument(
    "--sourcefile",
    dest="sourcefile",
    required=True,
    help="File to add to repository, pulled from local file system.",
)
parser.add_argument(
    "--destinationfile",
    dest="destinationfile",
    required=True,
    help="Where to add file in repository, format: dira/dirb/filename.xyz",
)
parser.add_argument(
    "--overwrite",
    dest="overwrite",
    action="store_true",
    default=False,
    help="If set, then allow destination file to be overwritten if it already exists, otherwise script will exit with error",
)
parser.add_argument(
    "--message",
    dest="message",
    required=True,
    help="message to use in commit message and pull request if creating one",
)
parser.add_argument(
    "--pullrequest",
    choices=["create", "merge", "delete"],
    default=None,
    help="Where to create a pull request, create and merge, or create, merge, then delete, requires branch and title to be set. Default is no pull request created",
)
parser.add_argument(
    "--branch",
    dest="branch",
    default=None,
    help="Branch to add file to in org/repo format, otherwise default branch is used. If same as basebranch, commit is made directly to the branch",
)
parser.add_argument(
    "--basebranch",
    dest="basebranch",
    default=None,
    help="Base branch to create new branch from, otherwise default branch is used. If same as branch, commit is made directly to the branch",
)
parser.add_argument(
    "--title",
    dest="title",
    help="Title of pull request, if creating one",
)
args = parser.parse_args()

## Get API token from environment variable
token = os.getenv("GITHUB_TOKEN")
if token is None:
    raise SystemExit("Environment variable GITHUB_TOKEN must be set")

# Used in multiple functions
urlBase = args.url
repo = args.repo
branch = args.branch
basebranch = args.basebranch
sourcefile = args.sourcefile
destinationfile = args.destinationfile
overwrite = args.overwrite
message = args.message
title = args.title
pullrequest = args.pullrequest
filesha = None

## Headers passed to every API call
headers = {
    "Content-Type": "application/json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {token}",
}

# Hit the GitHub API and return the JSON response
# url: URL to hit
# method: HTTP method to use (default: GET)
# headers: HTTP headers to use
# data: Data to send in the request (default: {})
# allowRedirects: Allow redirects, otherwise return empty JSON (default: True)
#   Transferred repos return 301 redirects to their new home
# allowNotFound: Accept 404 errors silently (default: False)
#   Used to ignore 404 errors when checking if something exists
# Sleeps for 1 second after doing mutative requests (PUT, POST, DELETE) as per GitHub Rest API best practices
def getJsonResponse(url,method="GET",headers=headers,data={},allowRedirects=True, allowNotFound=False):
    jsonResponse = {}
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, allow_redirects=allowRedirects)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, data=data)
            time.sleep(1)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=data)
            time.sleep(1)
        elif method == "PUT":
            response = requests.put(url, headers=headers, data=data)
            time.sleep(1)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
            time.sleep(1)
        else:
            print(f"Unsupported method: {method}")
            exit(1)
        response.raise_for_status()

        if allowRedirects == False and response.status_code == 301:
            jsonResponse = {}
        elif response.text:
            jsonResponse = response.json()

    except HTTPError as http_err:
        # Debugging why this happens sometimes
        if http_err.response.status_code == 422:
            print(
                f"ERROR: API responds with validation failed, response was {response.content}"
            )
        if allowNotFound:
           if http_err.response.status_code != 404:
            print(f"ERROR: HTTP error occured: {http_err} while accessing {url}")
            exit(1)
        else:
            print(f"ERROR: HTTP error occured: {http_err} while accessing {url}")
            exit(1)

    except Exception as err:
        print(f"ERROR: Other error occured: {err} while accessing {url}")
        exit(1)
    return jsonResponse

def getSourceFileContent(sourcefile):
    with open(sourcefile, "r") as f:
        return f.read()

def getDefaultBranch(repo):
    url = f"{urlBase}/repos/{repo}"
    response=getJsonResponse(url, allowNotFound=True)
    if response:
      return response["default_branch"]
    else:
      return None

def getBranch(repo, branch):
    url = f"{urlBase}/repos/{repo}/branches/{branch}"
    return getJsonResponse(url=url, allowNotFound=True)

def createBranch(repo, basebranch, branch):
    # Get sha of basebranch
    url = f"{urlBase}/repos/{repo}/branches/{basebranch}"
    response=getJsonResponse(url)
    sha=response["commit"]["sha"] 

    # Create new branch
    url = f"{urlBase}/repos/{repo}/git/refs"
    data = {
        "ref": f"refs/heads/{branch}",
        "sha": sha
    }
    return getJsonResponse(url=url,method="POST",data=json.dumps(data))

def getFileSha(repo, path, branch):
    # Get sha of file, or nothing if it doesn't exist
    url = f"{urlBase}/repos/{repo}/contents/{path}?ref={branch}"
    response=getJsonResponse(url=url, allowNotFound=True)
    if response:
        return response["sha"]
    else:
        return None

def putFile(repo,branch, path, encodedFileContent, message, filesha):
    url = f"{urlBase}/repos/{repo}/contents/{path}"

    # If we have a filesha, we are updating an existing file, so need to pass it
    if filesha:
        body = { 
        "message": message,
        "branch": branch,
        "content": encodedFileContent,
        "sha": filesha
        }
    else:
        body = { 
        "message": message,
        "branch": branch,
        "content": encodedFileContent
        }
    return getJsonResponse(url=url,method="PUT",data=json.dumps(body))

def createPR(repo,branch,basebranch,title,body):
    url = f"{urlBase}/repos/{repo}/pulls"
    body = { 
      "title": title,
      "body": body,
      "base": basebranch,
      "head": branch,
    }
    response=getJsonResponse(url=url,method="POST",data=json.dumps(body))
    return response["number"]

def mergePR(repo,pullnumber):
    url = f"{urlBase}/repos/{repo}/pulls/{pullnumber}/merge"
    return getJsonResponse(url=url,method="PUT")

def deleteBranch(repo,branch):
    url = f"{urlBase}/repos/{repo}/git/refs/heads/{branch}"
    return getJsonResponse(url=url,method="DELETE")

def validateArgs():
    
    global branch
    global basebranch
    global filesha

    if pullrequest:
        if not title:
            print(f'ERROR: Title must be set if creating a pull request')
            exit(1)
        elif not branch:
            print(f'ERROR: Branch must be set if creating a pull request')
            exit(1)
            
    if not os.path.exists(sourcefile):
        print(f'ERROR: Source file {sourcefile} does not exist')
        exit(1)
    
    if not re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$', repo):
        print(f'ERROR: Repo {repo} is not in org/repo format')
        exit(1)
    
    # Check that the repo exists by getting the default branch
    defaultBranch=getDefaultBranch(repo)
    if not defaultBranch:
      print(f'ERROR: Repo {repo} does not exist or is not readable')    
      exit(1)

    # Get the branch we are making changes to, if not set use default branch
    if not branch:
        branch=defaultBranch

    # Get the base branch that we are creating our branch from, if not set use default branch
    if not basebranch:
        basebranch=defaultBranch
    else:
        # Using a different base branch, lets check if it exists
        if not re.match(r'^[a-zA-Z0-9_.-]+$', basebranch):
            print(f'ERROR: Base branch {basebranch} is not in branch format')
            exit(1)
        response=getBranch(repo=repo, branch=basebranch)
        if not response:
            print(f'ERROR: Repo {repo} base branch {basebranch} does not exist')    
            exit(1)
    
    # Are we updating a branch directly or creating a new branch?
    if basebranch == branch:
        # Updating a branch directly, no pull request
        if pullrequest:
            print(f'ERROR: Cannot create pull request using same branch and basebranch {branch}')
            exit(1)
    else:
        # We are creating a new branch
        # Lets check the name and if it already exists
        if not re.match(r'^[a-zA-Z0-9_.-]+$', branch):
            print(f'ERROR: Branch {branch} is not in branch format')
            exit(1)
        response=getBranch(repo=repo, branch=branch)
        if response:
            print(f'ERROR: Repo {repo} branch {branch} already exists')    
            exit(1) 

    # Check if file we are adding already exists in the basebranch
    response=getFileSha(repo=repo, path=destinationfile, branch=basebranch)
    if response:
        if not overwrite:
            print(f'ERROR: File {destinationfile} already exists in {repo} branch {basebranch}')
            exit(1)
        else:
            # Overwriting is allow, we'll need the sha of the file to update it
            filesha=response

def main():
    print(f'Validating script arguments')
    validateArgs()

    print(f'Reading and encoding file content from {sourcefile}')
    fileContent=getSourceFileContent(sourcefile)
    encodedFileContent=base64.b64encode(fileContent.encode("utf-8")).decode("utf-8")

    if basebranch != branch:
        # Create a branch
        print(f'Creating repo {repo} branch {branch} from base branch {basebranch}')
        createBranch(repo=repo, basebranch=basebranch, branch=branch)

    print(f'Adding file to {repo} branch {branch}')
    putFile(repo=repo, encodedFileContent=encodedFileContent, branch=branch, path=destinationfile, message=message, filesha=filesha)

    if pullrequest:
      print(f'Creating pull request for {repo} branch {branch} for base branch {basebranch}')
      pullnumber=createPR(repo=repo, branch=branch, basebranch=basebranch, title=title, body=message)
      if pullrequest == 'merge' or pullrequest == 'delete':
          print(f'Merge pull request for {repo} branch {branch} for base branch {basebranch}')
          mergePR(repo=repo, pullnumber=pullnumber)    
          if pullrequest == 'delete':
              print(f'Delete branch {branch} for repo {repo}')
              deleteBranch(repo=repo, branch=branch)
    print(f'Complete')

if __name__ == "__main__":
    main()