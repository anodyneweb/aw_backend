from api.models import Station
from anodyne import PCBS


class ToPCB:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def upload(self):
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
            station = Station.objects.get(uuid=self.kwargs.get('station'))
            pcb = station.pcb
            pcb_obj = getattr(PCBS, pcb, None)
            # from anodyne.PCBS import mppcb
            # mppcb.Handle()
            if pcb_obj:
                message = '%s not yet configured.'
            else:
                Handle = getattr(pcb_obj, 'Handle')
                handle = Handle(**self.kwargs)
                status, message = handle.upload()

            response['success'] = status
            response['msg'] = message
        except Exception as err:
            response['msg'] = err

        return to_db_info
