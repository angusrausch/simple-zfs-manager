import sys
from app.core.zfs.models import PoolState, VDevNode

value = [PoolState(
    name='test', health='ONLINE', size=476741369856, allocated=218112, 
    free=476741151744, read_errors=0, write_errors=0, checksum_errors=0, 
    vdev_tree=VDevNode(
        name='test', vdev_type='root', state='ONLINE', path=None, read_errors=0, 
        write_errors=0, checksum_errors=0, 
        vdevs={'raidz1-0': VDevNode(
            name='raidz1-0', vdev_type='raidz', state='ONLINE', path=None, 
            read_errors=0, write_errors=0, checksum_errors=0, 
            vdevs={
                'sda': VDevNode(
                    name='sda', vdev_type='disk', state='ONLINE', path='/dev/sda1', 
                    read_errors=0, write_errors=0, checksum_errors=0, vdevs=None), 
                'sdb': VDevNode(
                    name='sdb', vdev_type='disk', state='ONLINE', path='/dev/sdb1', 
                    read_errors=0, write_errors=0, checksum_errors=0, vdevs=None)
                }
            )}
        )
)]