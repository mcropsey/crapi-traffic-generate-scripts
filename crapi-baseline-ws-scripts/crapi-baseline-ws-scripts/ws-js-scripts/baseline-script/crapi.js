import config from './config.js'
import axios from 'axios'
import { downloadFile } from './helpers.js'
import { createReadStream } from 'fs'
import { fileFromPath } from 'formdata-node/file-from-path'
import temp from 'temp'

export async function crapiRequest(url, method, data, headers, params) {
  if (!headers || !headers['Content-Type']) {
    headers = {
      ...headers,
      'Content-Type': 'application/json',
    }
  }
  return new Promise((resolve, reject) => {
    axios({
      method,
      url,
      data,
      params,
      headers,
      baseURL: config.crapi,
    })
      .then(resp => resolve(resp))
      .catch(err => reject(err))
  })
}

export async function register(user) {
  return await crapiRequest('/identity/api/auth/signup', 'POST', {
    email: user.email,
    password: user.password,
    name: user.name,
    number: user.number,
  })
}

export async function login(user) {
  return await crapiRequest('/identity/api/auth/login', 'POST', {
    email: user.email,
    password: user.password,
  })
}

export async function dashboard(user) {
  return await crapiRequest('/identity/api/v2/user/dashboard', 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function getVehicles(user) {
  return await crapiRequest('/identity/api/v2/vehicle/vehicles', 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function addVehicle(user, vin, pincode) {
  return await crapiRequest('/identity/api/v2/vehicle/add_vehicle', 'POST', { vin, pincode }, { Authorization: `Bearer ${user.token}` })
}

export async function getVehicleLocation(user, id) {
  return await crapiRequest(`/identity/api/v2/vehicle/${id}/location`, 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function getMechanics(user) {
  return await crapiRequest('/workshop/api/mechanic', 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function getProducts(user) {
  return await crapiRequest('/workshop/api/shop/products', 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function placeOrder(user, product_id, quantity) {
  return await crapiRequest('/workshop/api/shop/orders', 'POST', { product_id, quantity }, { Authorization: `Bearer ${user.token}` })
}

export async function changeEmail(user, old_email, new_email) {
  return await crapiRequest('/identity/api/v2/user/change-email', 'POST', { old_email, new_email }, { Authorization: `Bearer ${user.token}` })
}

export async function forgotPassword(email) {
  return await crapiRequest('/identity/api/auth/forget-password', 'POST', { email }, undefined)
}

export async function retrieveOrder(user, order_id) {
  return await crapiRequest(`/workshop/api/shop/orders/${order_id}`, 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function resendVehicleEmail(user) {
  return await crapiRequest('/identity/api/v2/vehicle/resend_email', 'POST', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function updateOrder(user, order_id, product_id, quantity) {
  return await crapiRequest(`/workshop/api/shop/orders/${order_id}`, 'PUT', { product_id, quantity }, { Authorization: `Bearer ${user.token}` })
}

export async function getPastOrders(user) {
  return await crapiRequest('/workshop/api/shop/orders/all', 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function returnOrder(user, orderId) {
  return await crapiRequest('/workshop/api/shop/orders/return_order', 'POST', undefined, { Authorization: `Bearer ${user.token}` }, { order_id: orderId })
}

export async function getRecentPosts(user) {
  return await crapiRequest('/community/api/v2/community/posts/recent', 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function getPost(user, postId) {
  if (!user.token) return
  return await crapiRequest(`/community/api/v2/community/posts/${postId}`, 'GET', undefined, { Authorization: `Bearer ${user.token}` })
}

export async function addComment(user, postId, content) {
  return await crapiRequest(`/community/api/v2/community/posts/${postId}/comment`, 'POST', { content }, { Authorization: `Bearer ${user.token}` })
}

export async function makePost(user, title, content) {
  return await crapiRequest('/community/api/v2/community/posts', 'POST', { title, content }, { Authorization: `Bearer ${user.token}` })
}

export async function addCoupon(user, coupon_code, amount) {
  return await crapiRequest('/community/api/v2/coupon/new-coupon', 'POST', { coupon_code, amount }, { Authorization: `Bearer ${user.token}` })
}

export async function validateCoupon(user, coupon_code) {
  return await crapiRequest('/community/api/v2/coupon/validate-coupon', 'POST', { coupon_code }, { Authorization: `Bearer ${user.token}` })
}

export async function applyCoupon(user, coupon_code, amount) {
  return await crapiRequest('/workshop/api/shop/apply_coupon', 'POST', { coupon_code, amount }, { Authorization: `Bearer ${user.token}` })
}

export async function makeMechanicReport(user, vin, mechanic_code, problem_details) {
  const result = await crapiRequest(
    '/workshop/api/merchant/contact_mechanic',
    'POST',
    {
      vin,
      mechanic_code,
      problem_details,
      mechanic_api: `${config.crapi}/workshop/api/mechanic/receive_report`,
      repeat_request_if_failed: false,
      number_of_repeats: 1,
    },
    { Authorization: `Bearer ${user.token}` }
  )
  return result
}

export async function getMechanicReport(user, report_id) {
  const result = await crapiRequest('/workshop/api/mechanic/mechanic_report', 'GET', null, { Authorization: `Bearer ${user.token}` }, { report_id })
  return result
}

export async function setVideo(user) {
  const formData = new FormData()
  formData.append('file', await fileFromPath('file_example_MOV_480_700kB.mov'))

  return await crapiRequest('/identity/api/v2/user/videos', 'POST', formData, { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${user.token}` })
}

export async function changeVideoName(user, id, videoName) {
  return await crapiRequest(`/identity/api/v2/user/videos/${id}`, 'PUT', { videoName }, { Authorization: `Bearer ${user.token}` })
}

export async function setAvatar(user) {
  const file = temp.path({ suffix: '.jpg' })
  console.log(file)
  await downloadFile(user.avatar, file)

  const formData = new FormData()
  formData.append('file', await fileFromPath(file))

  return await crapiRequest('/identity/api/v2/user/pictures', 'POST', formData, { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${user.token}` })
}
