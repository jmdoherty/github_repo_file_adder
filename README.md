# Add a file to a GitHub repo

This script is used to add a file to a GitHub repository, either directly or via a pull request, using the GitHub REST API.

Branch protection rules that block what you are trying to do will cause client errors to be thrown, such as
- Updating a branch that requires a pull request before merging
- Merge a pull request on a branch that requires approvals

Update the branch protection rules to allow bypass

```
usage: add_file_to_repo.py [-h] [--url URL] --repo REPO --sourcefile SOURCEFILE --destinationfile DESTINATIONFILE [--overwrite] --message MESSAGE [--pullrequest {create,merge,delete}] [--branch BRANCH] [--basebranch BASEBRANCH] [--title TITLE]

Add a file to a repository, either directly or thru pull requests

options:
  -h, --help            show this help message and exit
  --url URL             URL of Github API endpoint (default: https://api.github.com)
  --repo REPO           Repository to add file to in org/repo format (default: None)
  --sourcefile SOURCEFILE
                        File to add to repository, pulled from local file system. (default: None)
  --destinationfile DESTINATIONFILE
                        Where to add file in repository, format: dira/dirb/filename.xyz (default: None)
  --overwrite           If set, then allow destination file to be overwritten if it already exists, otherwise script will exit with error (default: False)
  --message MESSAGE     message to use in commit message and pull request if creating one (default: None)
  --pullrequest {create,merge,delete}
                        Where to create a pull request, create and merge, or create, merge, then delete, requires branch and title to be set. Default is no pull request created (default: None)
  --branch BRANCH       Branch to add file to in org/repo format, otherwise default branch is used. If same as basebranch, commit is made directly to the branch (default: None)
  --basebranch BASEBRANCH
                        Base branch to create new branch from, otherwise default branch is used. If same as branch, commit is made directly to the branch (default: None)
  --title TITLE         Title of pull request, if creating one (default: None)
```

Examples:

This updates the default branch of the james-demo-01 repository in the arctiq-partner-demo-emu-01 organization, adding the contents of local file ```test_file.yaml``` into the repo at ```.somedir/jmd9.txt```. The commit message is passed via ```--message```
```
python add_file_to_repo.py --repo arctiq-partner-demo-emu-01/james-demo-01 --message "Message here" --sourcefile test_file.yaml --destinationfile .somedir/jmd9.txt
Validating script arguments
Reading and encoding file content from test_file.yaml
Adding file to arctiq-partner-demo-emu-01/james-demo-01 branch master
Complete
```

If branch protection requires a pull request before merging, we would get this
```
python add_file_to_repo.py --repo arctiq-partner-demo-emu-01/james-demo-01 --message "Message here" --sourcefile test_file.yaml --destinationfile .somedir/jmd9.txt                       (main|…4)
Validating script arguments
Reading and encoding file content from test_file.yaml
Adding file to arctiq-partner-demo-emu-01/james-demo-01 branch master
ERROR: HTTP error occured: 409 Client Error: Conflict for url: https://api.github.com/repos/arctiq-partner-demo-emu-01/james-demo-01/contents/.somedir/jmd9.txt while accessing https://api.github.com/repos/arctiq-partner-demo-emu-01/james-demo-01/contents/.somedir/jmd9.txt
```

We can do the same update, except using a pull request using this command. In this case, we create a branch called ```jmdtest101``` and make the update there. A pull request is created and then merged. We also added the ```--overwrite``` flag because the destination file already exists and we want to overwrite it. For a pull request we have also have to provide a title via ```--title```. 
```
python add_file_to_repo.py --repo arctiq-partner-demo-emu-01/james-demo-01 --message "Message here" --sourcefile test_file.yaml --destinationfile .somedir/jmd9.txt --branch jmdtest101 --overwrite --pullrequest merge --title 'hi look at me'
Validating script arguments
Reading and encoding file content from test_file.yaml
Creating repo arctiq-partner-demo-emu-01/james-demo-01 branch jmdtest101 from base branch master
Adding file to arctiq-partner-demo-emu-01/james-demo-01 branch jmdtest101
Creating pull request for arctiq-partner-demo-emu-01/james-demo-01 branch jmdtest101 for base branch master
Merge pull request for arctiq-partner-demo-emu-01/james-demo-01 branch jmdtest101 for base branch master
Complete
```




