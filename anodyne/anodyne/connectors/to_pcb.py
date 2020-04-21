from anodyne.PCBS import MPPCB, HSPCB
from api.models import Station


class ToPCB:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.basename = kwargs.get('basename')

    def upload(self):
        # TODO: send station details in response to know update status in
        #  StationInfo
        response = {
            'success': False,
            'msg': ''
        }
        to_db_info = {
            'to_pcb': response
        }
        try:
            status = False
            message = ''
            # Process to PCBs
            station = Station.objects.get(prefix=self.kwargs.get('prefix'))
            pcb = station.pcb.name
            if pcb == 'MPPCB':
                pcb_obj = MPPCB
            elif pcb == 'HSPCB':
                pcb_obj = HSPCB
            else:
                pcb_obj = None
                message = '%s: PCB %s not configured' % (self.basename, pcb)

            if pcb_obj:
                Handle = getattr(pcb_obj, 'Handle')
                handle = Handle(**self.kwargs)
                status, message = handle.upload()

            response['success'] = status
            response['msg'] = message
        except Exception as err:
            response['msg'] = err

        return to_db_info
