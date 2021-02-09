#/bin/bash
if ! pgrep -x "vmware-remotemk" > /dev/null && ! pgrep -x "wfica" > /dev/null
then
    echo "No active session detected, iGEL is now Rebooting."
 #get latest settings from UMS
  get_rmsettings_boot
 #Clear the Imprivata Data Partition
  rm -rf /.imprivata_data/runtime
 #reboot the device
  echo "1"
  sleep 1
  reboot

else
    echo "Active session detected, iGEL will NOT Reboot."
fi

