import { faker } from '@faker-js/faker'
import { generate as generatePassword } from 'generate-password'

const inUseEmails = []
const inUsePhoneNumbers = []

const generateUniqueEmail = (firstName, lastName) => {
  var email;
  do {
    email = faker.internet.email(firstName, lastName)
  } while (!email || inUseEmails.includes(email))
  inUseEmails.push(email)
  return email
}

const generateUniquePhone = () => {
  var phone;
  do {
    phone = faker.phone.number('##########')
  } while (!phone || inUsePhoneNumbers.includes(phone))
  inUsePhoneNumbers.push(phone)
  return phone
}

export default () => {
  const firstName = faker.name.firstName()
  const lastName = faker.name.lastName()
  return {
    name: `${firstName} ${lastName}`,
    email: generateUniqueEmail(firstName, lastName),
    new_email: generateUniqueEmail(firstName, lastName),
    password: generatePassword({ length: 15, numbers: true, uppercase: true, lowercase: true, symbols: true }),
    number: generateUniquePhone(),
    userAgent: faker.internet.userAgent(),
    avatar: faker.internet.avatar(),
  }
}