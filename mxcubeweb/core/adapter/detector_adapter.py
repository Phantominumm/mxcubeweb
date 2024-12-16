from mxcubeweb.core.adapter.adapter_base import AdapterBase
from mxcubeweb.core.models.configmodels import AdapterResourceHandlerConfigModel

resource_handler_config = AdapterResourceHandlerConfigModel(
    name="detector_test", url_prefix="/mxcube/api/v0.1/detectortest", commands=["data"]
)


class DetectorAdapter(AdapterBase):
    def __init__(self, ho, role, app):
        """
        Args:
            (object): Hardware object.
        """
        super(DetectorAdapter, self).__init__(ho, role, app, resource_handler_config)
        ho.connect("stateChanged", self._state_change)

    def _state_change(self, *args, **kwargs):
        self.state_change(*args, **kwargs)

    def state(self):
        return self._ho.get_state().name.upper()
