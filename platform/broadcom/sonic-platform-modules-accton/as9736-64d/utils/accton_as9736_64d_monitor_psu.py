#!/usr/bin/env python
#
# Copyright (C) 2018 Accton Technology Corporation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------
# HISTORY:
#    mm/dd/yyyy (A.D.)
#    04/23/2021:  Michael_shih create for as9736-64d
# ------------------------------------------------------------------

try:
    import getopt
    import sys
    import logging
    import logging.config
    import logging.handlers
    import signal
    import time  # this is only being used as part of the example
except ImportError as e:
    raise ImportError('%s - required module not found' % str(e))

# Deafults
VERSION = '1.0'
FUNCTION_NAME = '/usr/local/bin/accton_as9736_64d_monitor_psu'

psu_state=[2, 2]
psu_status_state=[2, 2]

exit_by_sigterm=0

# Make a class we can use to capture stdout and sterr in the log
class device_monitor(object):

    def __init__(self, log_file, log_level):

        self.psu_num = 2
        self.psu_path = "/sys/bus/i2c/devices/"
        self.presence = "/psu_present"
        self.oper_status = "/psu_power_good"
        self.mapping = {
            0: "41-0051",
            1: "33-0050",
        }

        """Needs a logger and a logger level."""
        # set up logging to file
        logging.basicConfig(
            filename=log_file,
            filemode='w',
            level=log_level,
            format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        # set up logging to console

        if log_level == logging.DEBUG:
            console = logging.StreamHandler()
            console.setLevel(log_level)
            formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

        sys_handler = logging.handlers.SysLogHandler(address = '/dev/log')
        #sys_handler.setLevel(logging.WARNING)
        sys_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('#%(module)s: %(message)s')
        sys_handler.setFormatter(formatter)
        logging.getLogger('').addHandler(sys_handler)

        #logging.debug('SET. logfile:%s / loglevel:%d', log_file, log_level)

    def manage_psu(self):

        PSU_STATE_REMOVE = 0
        PSU_STATE_INSERT = 1

        PSU_STATUS_NO_POWER = 0
        PSU_STATUS_POWER_GOOD = 1
        PSU_STATUS_IDLE =2

        global psu_state

        for idx in range (0, self.psu_num):
            node = self.psu_path + self.mapping[idx] + self.presence
            try:
                val_file = open(node)
            except IOError as e:
                print("Error: unable to open file: %s" % str(e))
                return False
            content = val_file.readline().rstrip()
            val_file.close()
            # content is a string, either "0" or "1"
            if content == "1":
                if psu_state[idx]!=1:
                    psu_state[idx]=PSU_STATE_INSERT
                    logging.info("PSU-%d present is detected", idx+1);
                    #psu_status_state[idx]=PSU_STATUS_POWER_GOOD #when insert, assume power is good. If no_power, next code will find it.
            else:
                if psu_state[idx]!=0:
                    psu_state[idx]=PSU_STATE_REMOVE
                    logging.warning("Alarm for PSU-%d absent is detected", idx+1);
                    psu_status_state[idx]=PSU_STATUS_IDLE

        for idx in range (0, self.psu_num):
            node = self.psu_path + self.mapping[idx] + self.oper_status
            try:
                val_file = open(node)
            except IOError as e:
                print("Error: unable to open file: %s" % str(e))
                return False
            content = val_file.readline().rstrip()
            val_file.close()
            # content is a string, either "0" or "1"
            if content == "0":
                if psu_status_state[idx]!=PSU_STATUS_NO_POWER:
                    if psu_state[idx]==PSU_STATE_INSERT:
                        logging.warning("Alarm for PSU-%d failed is detected", idx+1);
                        psu_status_state[idx]=PSU_STATUS_NO_POWER
            else:
                if psu_state[idx]==PSU_STATE_INSERT:
                    if psu_status_state[idx]!=PSU_STATUS_POWER_GOOD:
                        logging.info("PSU-%d power_good is detected", idx+1);
                        psu_status_state[idx]=PSU_STATUS_POWER_GOOD


        return True

def signal_handler(sig, frame):
    global exit_by_sigterm
    if sig == signal.SIGTERM:
        print("Caught SIGTERM - exiting...")
        exit_by_sigterm = 1
    else:
        pass

def main(argv):
    log_file = '%s.log' % FUNCTION_NAME
    log_level = logging.INFO
    global exit_by_sigterm
    signal.signal(signal.SIGTERM, signal_handler)
    if len(sys.argv) != 1:
        try:
            opts, args = getopt.getopt(argv,'hdl:',['lfile='])
        except getopt.GetoptError:
            print('Usage: %s [-d] [-l <log_file>]' % sys.argv[0])
            return 0
        for opt, arg in opts:
            if opt == '-h':
                print('Usage: %s [-d] [-l <log_file>]' % sys.argv[0])
                return 0
            elif opt in ('-d', '--debug'):
                log_level = logging.DEBUG
            elif opt in ('-l', '--lfile'):
                log_file = arg
    monitor = device_monitor(log_file, log_level)
    # Loop forever, doing something useful hopefully:
    while True:
        monitor.manage_psu()
        time.sleep(3)
        if exit_by_sigterm == 1:
            break

if __name__ == '__main__':
    main(sys.argv[1:])

