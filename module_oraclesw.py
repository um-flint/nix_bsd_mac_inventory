from xml.dom import minidom
# We don't execute any commands as root
# Seemed more secure to assume the discovery user is a member of the oinstall group

def get_oracle_inventory_loc(self,os=linux):
    inventory_loc = ''

    # These paths were taken from https://docs.oracle.com/cd/E18283_01/em.112/e12255/oui2_manage_oracle_homes.htm#CJAEHIGJ
    # Default to using Linux path
    inventory_pointer = '/etc/oraInst.loc'
    if (os == 'solaris') or (os == 'aix') or (os == 'hpux')
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
        oracle_software = {}
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
            
            #Most Oracle homes seem to have only 1 top level product - this makes sense
            #However, I have seen some Enterprise Manager 13c Agent homes that have 50+
            #Rather than pull in all of these components, look for the top level one used by Agent 12c
            if len(comps) == 1:
                component_name = comps[0].attributes['NAME'].value
                component_version = comps[0].attributes['VER'].value
                component_extended_name = comps[0].getElementsByTagName('EXT_NAME')[0].firstChild.data
            else:
                for comp in comps:
                    component_name = comp.attributes['NAME'].value
                    if component_name == 'oracle.sysman.top.agent':
                        component_version = comp.attributes['VER'].value
                        component_extended_name = comp.getElementsByTagName('EXT_NAME')[0].firstChild.data

            oracle_software.update({'software': component_extended_name})
            oracle_software.update({'vendor': 'Oracle Corporation'})
            oracle_software.update({'version': component_version})
            oracle_software.update({'device': self.device_name})
        else:
            print data_err

        return oracle_software

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

            # If an Oracle Home is uninstalled / removed it is not deleted from the inventory
            # The REMOVED attribute added and set to 'T'
            if home.hasAttribute('REMOVED'):
                removed = home.attributes['REMOVED']
                if removed.value == 'F':
                    oracle_homes.append(loc)
            else:
                oracle_homes.append(loc)

    return oracle_homes

def get_oraclesoftware(self):
    oracle_software = []

    oracle_inventory_loc = get_oracle_inventory_loc(self)
    if oracle_inventory_loc is not '':
        oracle_homes = get_oracle_homes(self,oracle_inventory_loc)
        if oracle_homes is not []:
            for oracle_home in oracle_homes:
                self.oracle_software.append(get_oracle_home_details(self,oracle_home))
        else:
            print 'No homes found in the Oracle Central Inventory!'
    else:
        print 'Could not find Oracle Central Inventory!'

    return oracle_software