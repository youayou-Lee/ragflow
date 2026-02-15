import api from '@/utils/api';
import registerServer from '@/utils/register-server';
import request, { post } from '@/utils/request';

const {
  login,
  logout,
  register,
  setting,
  user_info,
  tenant_info,
  factories_list,
  llm_list,
  my_llm,
  set_api_key,
  set_tenant_info,
  add_llm,
  delete_llm,
  enable_llm,
  deleteFactory,
  getSystemStatus,
  getSystemVersion,
  getSystemTokenList,
  removeSystemToken,
  createSystemToken,
  getSystemConfig,
  setLangfuseConfig,
  set_fallback_config,
  get_fallback_config,
} = api;

const methods = {
  login: {
    url: login,
    method: 'post',
  },
  logout: {
    url: logout,
    method: 'get',
  },
  register: {
    url: register,
    method: 'post',
  },
  setting: {
    url: setting,
    method: 'post',
  },
  user_info: {
    url: user_info,
    method: 'get',
  },
  get_tenant_info: {
    url: tenant_info,
    method: 'get',
  },
  set_tenant_info: {
    url: set_tenant_info,
    method: 'post',
  },
  factories_list: {
    url: factories_list,
    method: 'get',
  },
  llm_list: {
    url: llm_list,
    method: 'get',
  },
  my_llm: {
    url: my_llm,
    method: 'get',
  },
  set_api_key: {
    url: set_api_key,
    method: 'post',
  },
  add_llm: {
    url: add_llm,
    method: 'post',
  },
  delete_llm: {
    url: delete_llm,
    method: 'post',
  },
  enable_llm: {
    url: enable_llm,
    method: 'post',
  },
  getSystemStatus: {
    url: getSystemStatus,
    method: 'get',
  },
  getSystemVersion: {
    url: getSystemVersion,
    method: 'get',
  },
  deleteFactory: {
    url: deleteFactory,
    method: 'post',
  },
  listToken: {
    url: getSystemTokenList,
    method: 'get',
  },
  createToken: {
    url: createSystemToken,
    method: 'post',
  },
  removeToken: {
    url: removeSystemToken,
    method: 'delete',
  },
  getSystemConfig: {
    url: getSystemConfig,
    method: 'get',
  },
  setLangfuseConfig: {
    url: setLangfuseConfig,
    method: 'put',
  },
  getLangfuseConfig: {
    url: setLangfuseConfig,
    method: 'get',
  },
  deleteLangfuseConfig: {
    url: setLangfuseConfig,
    method: 'delete',
  },
  setFallbackConfig: {
    url: set_fallback_config,
    method: 'post',
  },
  getFallbackConfig: {
    url: get_fallback_config,
    method: 'get',
  },
} as const;

const userService = registerServer<keyof typeof methods>(methods, request);

export const getLoginChannels = () => request.get(api.login_channels);
export const loginWithChannel = (channel: string) =>
  (window.location.href = api.login_channel(channel));

export const listTenantUser = (tenantId: string) =>
  request.get(api.listTenantUser(tenantId));

export const addTenantUser = (tenantId: string, email: string) =>
  post(api.addTenantUser(tenantId), { email });

export const deleteTenantUser = ({
  tenantId,
  userId,
}: {
  tenantId: string;
  userId: string;
}) => request.delete(api.deleteTenantUser(tenantId, userId));

export const listTenant = () => request.get(api.listTenant);

export const agreeTenant = (tenantId: string) =>
  request.put(api.agreeTenant(tenantId));

// Fallback configuration interfaces and functions
export interface FallbackConfig {
  fallback_models: string[];
  fallback_factories: string[];
}

export interface FallbackByType {
  [modelType: string]: {
    models: string[];
    factories: string[];
  };
}

export interface AllFallbackConfig {
  fallback_by_type: FallbackByType;
}

export interface SetFallbackConfigParams {
  llm_factory: string;
  model_type: string;
  fallback_models?: string[];
  fallback_factories?: string[];
}

export const setFallbackConfig = (params: SetFallbackConfigParams) =>
  request.post(api.set_fallback_config, { data: params });

export const getFallbackConfig = (llm_factory: string, model_type?: string) =>
  request.get(api.get_fallback_config, {
    params: { llm_factory, ...(model_type && { model_type }) }
  });

export default userService;
