from supabase import create_client

url = "https://vnaeznlgijnarwqrwdtz.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZuYWV6bmxnaWpuYXJ3cXJ3ZHR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1Mjk4OTQsImV4cCI6MjA5MjEwNTg5NH0.kw8jhS-YErCJgDVkSDj6zBrJK3ytLnFS-2f0YR9D6hw"   # use anon for auth

supabase = create_client(url, key)

'''response = supabase.auth.sign_up({
    "email": "user@gmail.com",
    "password": "strongpassword"
})'''

response = supabase.auth.sign_in_with_password({
    "email": "user@gmail.com",
    "password": "strongpassword"
})

user = response.user
session = response.session

print("Unique ID:",user.id)   # ⭐ THIS IS YOUR UNIQUE ID

print(response)