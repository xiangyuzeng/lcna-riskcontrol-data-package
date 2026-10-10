SELECT /*+ MAX_EXECUTION_TIME(5000) */ VERSION() AS v, @@read_only AS ro, @@innodb_read_only AS iro, @@super_read_only AS sro, @@time_zone AS tz
