#!/usr/bin/python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import subprocess
import FoundationPlist

from DmgMounter import DmgMounter
from PkgCreator import PkgCreator
from autopkglib import Processor, ProcessorError


__all__ = ["AppDmgPkgCreator"]


class AppDmgPkgCreator(PkgCreator, DmgMounter):
    
    description = ("Repackages an application distributed on a drag-n-drop "
        "disk image into a flat package.")
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Disk image file containing the app to be packaged."
        },
        "app_path": {
            "required": False,
            "description": ("Relative path to the app from the root of the "
                "mounted disk image. If this is not defined, the first app at "
                "the root of the mounted dmg will be used.")
        },
        'pkgname': {
            "required": False,
            "description": ("Name for generated package; if not defined, "
                "defaults to simple name of the app plus version.")
        }
    }
    output_variables = {
        "pkg_path": {
            "description": "The created package.",
        },
    }
    
    __doc__ = description
    
    def __init__(self, data=None, infile=None, outfile=None):
        super(AppDmgPkgCreator, self).__init__(data, infile, outfile)
    
    def find_app(self, mount_point):
        '''Return path to the first .app found in mount_point'''
        for itemname in os.listdir(mount_point):
            if itemname.endswith(".app"):
                return os.path.join(mount_point, itemname)
        raise ProcessorError(
            "Can't find an application to package on %s" % self.env['dmg_path'])
            
    def get_app_info(self, app_path):
        '''Get some basic info about the app'''
        info_plist = os.path.join(app_path, "Contents/Info.plist")
        try:
            info = FoundationPlist.readPlist(info_plist)
        except FoundationPlist.FoundationPlistException as err:
            raise ProcessorError("Couldn't read %s: %s" % (info_plist, err))
        self.app_name = os.path.splitext(os.path.basename(app_path))[0]
        try:
            self.app_version = info["CFBundleShortVersionString"]
            self.app_identifier = info["CFBundleIdentifier"]
        except AttributeError as err:
            raise ProcessorError("Missing key in %s: %s" % (info_plist, err))
    
    def main(self):
        mount_point = None
        try:
            print "mounting dmg"
            mount_point = self.mount(self.env['dmg_path'])
            print "getting app"
            app_path = self.env.get("app_path") or self.find_app(mount_point)
            print "getting app info"
            self.get_app_info(app_path)
            print "getting pkg name"
            pkgname = (self.env.get("pkgname") or 
                       "%s-%s" % (self.app_name, self.app_version))
                       
            print "making pkg request"
            # build a pkg request
            self.env["pkg_request"] = {
                "pkgtype": "flat",
                "pkgroot": app_path,
                "pkgname": pkgname,
                "version": self.app_version,
                "id": self.app_identifier,
                "resources": "",
                "options": "",
                "infofile": "",
                "chown": [
                    {
                        "path": "Applications",
                        "user": "root",
                        "group": "admin"
                    }
                ]
            }
            # now make the package
            print "making package"
            self.package()
        except BaseException as err:
            raise ProcessorError(err)
        finally:
            if mount_point:
                self.unmount(self.env['dmg_path'])

if __name__ == '__main__':
    processor = AppDmgPkgCreator()
    processor.execute_shell()
