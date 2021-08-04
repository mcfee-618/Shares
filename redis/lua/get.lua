local num = KEYS[1]
redis.call('incr','key1')
redis.call('incr','key2')
local value = redis.call('get','key' .. num)
return value
