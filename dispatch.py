
"""
This is the main module.

Example:
    $ python dispatch.py --key <key_address> --host <host>
        --port <port> --user <user> <source> <desination>

When the script starts. It matches the contents of two folders.
If destination has files/folders not present in source,
then it deletes them

Then matches the current files/folder in the source direcory to destination directory

The utility also watches the contents of the source directory
and take acions based on changes of the directory.
"""
import argparse
import os
import sys
import signal
import time
import connector

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils import DSException

class DroidSync(object):
    """ Main DoidSync class

    Attributes:
        args (:obj:`string`) arguments specified during runtime
        source (str) Source folder to sync
        dest (str) Destination remote folder
        connection_client (:obj: connector.Connector) this is used to creat connection to remote host
        observer (:obj: Observer) The observer object of watchdog, that observe change in dir
    """
    def parse_args(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument('source', help='Enter the source folder location')
        parser.add_argument('dest', help='Enter the destination folder location')
        parser.add_argument('--key', dest='key', help='Key to be used to ssh')
        parser.add_argument('--host', dest='host', help='Host to ssh into')
        parser.add_argument('--port', dest='port', help='Port fot the host to ssh', type=int)
        parser.add_argument('--pass', dest='password', help='Password to use')
        parser.add_argument('--key-pass', dest='key_password', help='Password for the private key file')
        parser.add_argument('--user', dest='user', help='user to login as')
        self.args = parser.parse_args(args)

    def __init__(self, args):
        self.parse_args(args)
        self.source = self.args.source
        self.dest = self.args.dest
        self.connector_client = connector.Connector(self.args.key,
                                                    self.args.host,
                                                    self.args.port,
                                                    self.args.user,
                                                    self.args.password,
                                                    self.args.key_password)
        self.observer = Observer()

    def remove_files(self, source, dest):
        """Remove the files not present in source

            Args:
                source (str): source dir
                dest (str): destination dir
        """
        source_files = os.listdir(source)
        for name in self.connector_client.get_files_list(dest):
            if name not in source_files:
                self.connector_client.remove(dest, name)
            elif os.path.isdir(os.path.join(source, name)):
                self.remove_files(os.path.join(source, name), os.path.join(dest, name))

    def start(self):
        """Start method starts executing the main logic"""
        if not os.path.isdir(self.source):
            raise DSException('%s is not a directory' % self.source)

        self.connector_client.check_dest_dir(self.dest)
        self.remove_files(self.source, self.dest)
        source_files = os.listdir(self.source)
        for source_file in source_files:
            name = os.path.join(self.source, source_file)
            target_file = os.path.join(self.dest, source_file)
            self.connector_client.check_target(name, target_file)

        event_handler = Handler(droidsync=self)
        self.observer.schedule(event_handler, self.source, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    """Handler class that handles the event emitted

        The class is inherted from FileSystemEventHandler.
        on_any_event is invoked as soon as any file system related event
        is emmited

        Attributes:
            droidsync: (:obj: DroidDync) - the droidsync object

    """
    def __init__(self, droidsync, *args):
        super(Handler, self).__init__(*args)
        self.droidsync = droidsync

    def on_any_event(self, event):
        """ Method is called when any event occurs

            Args:
                event (:obj:) event object that initiated the handler
        """
        src_path = event.src_path[event.src_path.find(self.droidsync.source) + len(self.droidsync.source):]
        event_type = event.event_type
        if not os.path.normpath(self.droidsync.source) == event.src_path:
            if event_type == 'moved':
                self.droidsync.connector_client.remove(self.droidsync.dest, src_path)
                dest_path = event.dest_path[event.dest_path.find(self.droidsync.source) + len(self.droidsync.source):]
                self.droidsync.connector_client.check_target(event.dest_path, os.path.join(self.droidsync.dest, dest_path))

            if event_type == 'modified' or event_type == 'created':
                self.droidsync.connector_client.check_target(event.src_path, os.path.join(self.droidsync.dest, src_path))

            if event_type == 'deleted':
                self.droidsync.connector_client.remove(self.droidsync.dest, src_path)

def handle_signal(signal, frame):
    os._exit(0)

def main(args=None):
    """Main method

        Args:
            args (:obj:) arguments specified at runtime
    """
    signal.signal(signal.SIGINT, handle_signal)
    client = DroidSync(args)
    client.start()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))