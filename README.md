# DroidSync

The script will sync your local directory with a remote directory. The changes made on local will be reflected on remote.

The script has been tested with following setup-
* OS - Ubuntu14
* Python - 2.7
* pip - 9.0.1

Steps to run - 
* git clone <repo>
* cd <repo>
* pip install -r reqirements.txt
* python dispatch.py --key <your_pvt_key> --host <remote_host> --port <ssh_port> --user <ssh_user> <source> <dest>

Please make your you specify the port with ssh enabled and the user specified should have ample permissions to do the related operations.

