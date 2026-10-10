SELECT /*+ MAX_EXECUTION_TIME(5000) */ VERSION() AS v, @@read_only AS ro, @@time_zone AS tz, UTC_TIMESTAMP() AS db_utc
