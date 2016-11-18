from xml.dom import minidom
# We don't execute any commands as root
# Seemed more secure to assume the discovery user is a member of the oinstall group

def get_oracle_inventory_loc(self,os='linux'):
    inventory_loc = ''

    # These paths were taken from https://docs.oracle.com/cd/E18283_01/em.112/e12255/oui2_manage_oracle_homes.htm#CJAEHIGJ
    # Default to using Linux path
    inventory_pointer = '/etc/oraInst.loc'
    if (os == 'solaris') or (os == 'aix') or (os == 'hpux'):
        inventory_pointer = '/var/opt/oracle/oraInst.loc'

    if 'grep' in self.paths:
        cmd = "%s/grep inventory_loc %s" % (self.paths['grep'], inventory_pointer)
    else:
        cmd = "grep inventory_loc %s" % (inventory_pointer)
    data_out, data_err = self.execute(cmd)
    if not data_err:
        inventory_loc = data_out[0].split('=')[1].strip()
        
    return inventory_loc

def get_oracle_home_details(self, oracle_home):
        home_details = []
        # Middleware 12c homes using OUI 13.x have a file named registry.xml
        # Try to use this first to get the top level product
        # Refer to Doc ID 1591483.1 for more info
        if 'grep' in self.paths:
            cmd = "%s/cat %s/inventory/registry.xml" % (self.paths['cat'], oracle_home)
        else:
            cmd = "cat %s/inventory/registry.xml" % (oracle_home)
        data_out, data_err = self.execute(cmd)

        if not data_err:
            xmldoc = minidom.parseString(''.join(data_out))
            registry = xmldoc.getElementsByTagName('registry')[0]
            distributions = registry.getElementsByTagName('distributions')[0]
            for distribution in distributions.getElementsByTagName('distribution'):
                oracle_software = {}
                oracle_software.update({'software': distribution.attributes['name'].value})
                oracle_software.update({'vendor': 'Oracle Corporation'})
                oracle_software.update({'version': distribution.attributes['version'].value})
                oracle_software.update({'device': self.device_name})
                home_details.append(oracle_software)
        else:
            # comps.xml has only 1 top level product for 11g based middleware homes and database homes
            # 12c database homes have only 1 top level product as well
            # We don't want to use this for OUI 13.x based homes as there will be 50+ top level products
            if 'grep' in self.paths:
                cmd = "%s/cat %s/inventory/ContentsXML/comps.xml" % (self.paths['cat'], oracle_home)
            else:
                cmd = "cat %s/inventory/ContentsXML/comps.xml" % (oracle_home)
            data_out, data_err = self.execute(cmd)
            
            if not data_err:
                xmldoc = minidom.parseString(''.join(data_out))
                prd_list = xmldoc.getElementsByTagName('PRD_LIST')[0]
                tl_list = prd_list.getElementsByTagName('TL_LIST')[0]
                comps = tl_list.getElementsByTagName('COMP')
            
                for comp in comps:
                    oracle_software = {}
                    oracle_software.update({'software': comp.getElementsByTagName('EXT_NAME')[0].firstChild.data})
                    oracle_software.update({'vendor': 'Oracle Corporation'})
                    oracle_software.update({'version': comp.attributes['VER'].value})
                    oracle_software.update({'device': self.device_name})
                    home_details.append(oracle_software)

        return home_details

def get_oracle_homes(self, oracle_inventory_loc):
    oracle_homes = []

    if 'cat' in self.paths:
        cmd = "%s/cat %s/ContentsXML/inventory.xml" % (self.paths['cat'], oracle_inventory_loc)
    else:
        cmd = "cat %s/ContentsXML/inventory.xml" % (oracle_inventory_loc)
    data_out, data_err = self.execute(cmd)
    if not data_err:
        xmldoc = minidom.parseString(''.join(data_out))
        inventory = xmldoc.getElementsByTagName('INVENTORY')[0]
        home_list = inventory.getElementsByTagName('HOME_LIST')[0]
        homes = home_list.getElementsByTagName('HOME')
        for home in homes:
            loc = home.attributes['LOC'].value

            # If an Oracle Home is uninstalled / removed it is not deleted from the inventory file
            # The REMOVED attribute added and set to 'T'
            if home.hasAttribute('REMOVED') == False:
                oracle_homes.append(loc)

    return oracle_homes

def get_oraclesoftware(self):
    oracle_software = []

    oracle_inventory_loc = get_oracle_inventory_loc(self)
    if oracle_inventory_loc is not '':
        oracle_homes = get_oracle_homes(self,oracle_inventory_loc)
        if oracle_homes is not []:
            for oracle_home in oracle_homes:
                if self.debug:
                    print 'Processing Oracle Home ' + oracle_home
                for home_detail in get_oracle_home_details(self,oracle_home):
                    self.oracle_software.append(home_detail)
        else:
            if self.debug:
                print 'No homes found in the Oracle Central Inventory on ' + self.device_name
    else:
        if self.debug:
            print 'Could not find Oracle Central Inventory on ' + self.device_name
    return oracle_software