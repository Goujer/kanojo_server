#Kanojo Relationship Levels
RELATION_FRIEND = 3
RELATION_KANOJO = 2
RELATION_OTHER = 1

#User Relationship Status
USER_RELATION_ENEMY = 3
USER_RELATION_SELF = 2
USER_RELATION_OTHER = 1

#Live2D User Actions
USER_ACTION_SWIPE = 10
USER_ACTION_SHAKE = 11
USER_ACTION_HEADPAT = 12
USER_ACTION_KISS = 20
USER_ACTION_BREASTS = 21

#Store Item Classes
GIFT_ITEM_CLASS = 1
DATE_ITEM_CLASS = 2
TICKET_ITEM_CLASS = 3

# Which List to get from store, available for purchase or owned by user
TYPE_STORE = 1
TYPE_ITEM_LIST = 2

# after add new activity type add them to ALL_ACTIVITIES list
#    and fix "user_activity" and "all_activities" if need
ACTIVITY_SCAN = 1                           #   "Nightmare has scanned on 2014/10/04 05:31:50.\n"
ACTIVITY_GENERATED = 2                      # + "Violet was generated from 星光産業 ."
ACTIVITY_ME_ADD_FRIEND = 5                  # + "Filter added 葵 to friend list."
ACTIVITY_APPROACH_KANOJO = 7                # + "KH approached めりい."
ACTIVITY_ME_STOLE_KANOJO = 8                # + "Devourer stole うる from Nobody."
ACTIVITY_MY_KANOJO_STOLEN = 9               # + "ふみえ was stolen by Nobody."
ACTIVITY_MY_KANOJO_ADDED_TO_FRIENDS = 10    # + "呪いのBlu-ray added ぽいと to friend list."
ACTIVITY_BECOME_NEW_LEVEL = 11              # + "Everyone became Lev.\"99\"."
ACTIVITY_MARRIED = 15                       #   "Devourer get married with うる."

# user defined
# can change "activity_type" in "clear" function to show in client
ACTIVITY_JOINED = 101                       # +
ACTIVITY_BREAKUP = 102                      # +
ACTIVITY_ADD_AS_ENEMY = 103                 # +