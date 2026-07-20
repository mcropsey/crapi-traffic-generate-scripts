import config from './config.js'
import axios from 'axios'

export async function mailhogRequest(url, method, data, params, headers) {
  return new Promise((resolve, reject) => {
    axios({
      method,
      url,
      data,
      params,
      headers: { ...headers, 'Content-Type': 'application/json' },
      baseURL: `${config.mailhog}/api`,
    })
      .then(resp => resolve(resp))
      .catch(err => reject(err))
  })
}

export async function getEmails(limit = 50) {
  const result = await mailhogRequest('/v2/messages', 'GET', undefined, { limit })
  return result
}

export async function searchEmails(address) {
  const result = await mailhogRequest('/v2/search', 'GET', undefined, { kind: 'containing', query: address })
  return result
}

export async function getEmail(id) {
  const result = await mailhogRequest(`/v1/messages/${id}`, 'GET')
  return result
}
