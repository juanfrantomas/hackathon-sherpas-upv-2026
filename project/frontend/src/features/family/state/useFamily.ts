import { useContext } from 'react'
import {
  FamilyDataContext,
  NavigationContext,
  type FamilyDataValue,
  type NavigationValue,
} from './contexts'

/** The household being demoed, its state, and the actions that change it. */
export function useFamilyData(): FamilyDataValue {
  const value = useContext(FamilyDataContext)
  if (!value) {
    throw new Error('useFamilyData must be used inside a FamilyProvider')
  }
  return value
}

/** Where the user is inside the phone, and how to move. */
export function useNavigation(): NavigationValue {
  const value = useContext(NavigationContext)
  if (!value) {
    throw new Error('useNavigation must be used inside a FamilyProvider')
  }
  return value
}
