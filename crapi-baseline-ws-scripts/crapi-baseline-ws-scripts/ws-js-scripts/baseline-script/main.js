import { faker } from '@faker-js/faker'
import config from './config.js'
import createUser from './user.js'
import * as crapi from './crapi.js'
import * as mailhog from './mailhog.js'
import { PromisePool } from '@supercharge/promise-pool'

const janeDoe = {
  name: 'Jane Doe',
  email: 'jane.doe@fake.com',
  password: 'N0name!2023',
  number: '5555555555',
  userAgent: faker.internet.userAgent(),
  avatar: faker.internet.avatar(),
}

const johnSmith = {
  name: 'John Smith',
  email: 'john.smith@fake.com',
  password: 'N0name!2023',
  number: '5555555556',
  userAgent: faker.internet.userAgent(),
  avatar: faker.internet.avatar(),
}

const user1 = {
  name: 'John Smith',
  email: 'crapi_user1@nonamesec.com',
  password: 'N0name!2023',
  number: '5555555557',
  userAgent: faker.internet.userAgent(),
  avatar: faker.internet.avatar(),
}

const user2 = {
  name: 'Jane Doe',
  email: 'crapi_user2@nonamesec.com',
  password: 'N0name!2023',
  number: '5555555558',
  userAgent: faker.internet.userAgent(),
  avatar: faker.internet.avatar(),
}

const baselineUser = async (user, orderQuantity) => {
  try {
    if (!user) user = createUser()
    //register user
    await crapi.register(user)
    //login user
    const loginData = await crapi.login(user)
    user.token = loginData.data.token
    if (!user.token) return
    //simulate same API behavior that web UI generates
    await crapi.dashboard(user)
    await crapi.getVehicles(user)

    //baseline the mailhog UI functionality that users will be accessing later
    await mailhog.getEmails(50)

    //search for our user's registration email in order to get the vin
    const emailSearchResult = await mailhog.searchEmails(user.email)
    const ourEmail = emailSearchResult.data.items[0].ID
    const email = await mailhog.getEmail(ourEmail)
    const emailContent = email.data.Content.Body
    //parse the VIN.. crAPI doesn't produce valid VINs :( just a 17 digit alphanumeric
    const vinMatch = emailContent.match(config.vinRegex)
    const vin = vinMatch[0]
    //parse the pincode
    const pinMatch = emailContent.match(config.pinRegex)
    const pin = pinMatch[1]

    //add our vehicle
    await crapi.resendVehicleEmail(user)
    await crapi.addVehicle(user, vin, pin)
    //simulate the same API call behavior that web UI generates
    await crapi.dashboard(user)
    const vehicles = await crapi.getVehicles(user)
    const vehicleId = vehicles.data[0].uuid
    //'click' the refresh location button
    await crapi.getVehicleLocation(user, vehicleId)

    //set our avatar
    await crapi.setAvatar(user)

    //upload a video (skipped - no video file)
    // const video = await crapi.setVideo(user)
    // await crapi.changeVideoName(user, video.data.id, faker.system.commonFileName('mov'))

    //'click' contact mechanic
    await crapi.getMechanics(user)

    const mechanicReport = await crapi.makeMechanicReport(user, vin, 'TRAC_JHN', faker.lorem.sentence())
    await crapi.getMechanicReport(user, mechanicReport.data.response_from_mechanic_api.id)

    //'click' Shop
    const products = await crapi.getProducts(user)

    //validate a coupon
    const couponValidation = await crapi.validateCoupon(user, 'TRAC075')
    //apply coupon
    const applyCoupon = await crapi.applyCoupon(user, 'TRAC075', 75)

    //place an order and simulate web ui behavior
    const productId = products.data.products[0].id
    const order = await crapi.placeOrder(user, productId, orderQuantity ?? 1)
    await crapi.retrieveOrder(user, order.data.id)
    await crapi.updateOrder(user, order.data.id, productId, 2)
    const pastOrders = await crapi.getPastOrders(user)

    //return order
    const pastOrderId = pastOrders.data.orders[0].id
    await crapi.returnOrder(user, pastOrderId)

    //'click' on community
    const recentPosts = await crapi.getRecentPosts(user)
    //'read' all posts
    for (var post of recentPosts.data) {
      try {
        //add a comment to the post
        await crapi.addComment(user, post.id, faker.lorem.paragraph())
        //retrieve the post
        await crapi.getPost(user, post.id)
      } catch { }
    }

    //make a forum post; simulate webui behavior
    const myPost = await crapi.makePost(user, faker.lorem.sentence(), faker.lorem.paragraphs(2))
    await crapi.getPost(user, myPost.data.id)

    //change email address and forgot password
    await crapi.forgotPassword(user.email)
    await crapi.changeEmail(user, user.email, user.new_email)
  } catch (err) {
    if (user) console.log(`Error running baseline for ${user.email} / ${user.name}`)
    console.log(err)
  } //just keep going
}

console.log('Baseline started')
const users = [...Array(config.usersToSimulate)]
await PromisePool.withConcurrency(config.batchSize).for(users).process(baselineUser)
console.log('Baseline complete')

if (process.env.FIRST_RUN) {
  await baselineUser(janeDoe, -999999999)
  await baselineUser(johnSmith, -999999999)
  await baselineUser(user1, -999999999)
  await baselineUser(user2, -999999999)
}
