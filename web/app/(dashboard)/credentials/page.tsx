import CredentialsActions from "@/app/components/credentials"
import { CredentialsContextProvider } from "@/context/useCredentialsContext"

const CredentialsPage = () => {
  return (
    <CredentialsContextProvider>
      <CredentialsActions />
    </CredentialsContextProvider>
  )
}

export default CredentialsPage