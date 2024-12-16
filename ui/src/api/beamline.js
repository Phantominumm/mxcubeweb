import api from './api';

const endpoint = api.url('/beamline');

export function fetchBeamlineSetup() {
  return endpoint.get('/').safeJson();
}

export function fetchBeamInfo() {
  return endpoint.get('/beam/info').safeJson();
}

export function sendPrepareBeamlineForNewSample() {
  return endpoint.put(undefined, '/prepare_beamline').res();
}

export function sendExecuteCommand(object_type, object_id, command, args) {
  return api
    .url('/hwobj')
    .put({ args }, `/${object_type}/${object_id}/${command}`)
    .res();
}

export function sendSetAttribute(object_id, type, value) {
  return api
    .url('/hwobj')
    .put({ value }, `/${type}/${object_id}/set_value`)
    .res();
}

export function sendGetAttribute(object_id, type) {
  return api.url('/hwobj').put({}, `/${type}/${object_id}/get_value`).res();
}

export function sendRunBeamlineAction(name, parameters) {
  return endpoint.post({ parameters }, `/${name}/run`).res();
}

export function sendAbortBeamlineAction(name) {
  return endpoint.get(`/${name}/abort`).res();
}
