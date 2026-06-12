@echo off
setlocal enabledelayedexpansion

:: Database settings
set DATABASE_NAME=mydb
set USER=postgres
set BACKUP_DIR=C:\backups
set EXTERNAL_SSD_DRIVE=D:
set EXTERNAL2=F:
set EXTERNAL3=G:

:: Get timestamp (YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set ldt=%%I
set TIMESTAMP=!ldt:~0,8!_!ldt:~8,6!

:: Backup file with timestamp
@REM set BACKUP_FILE=%BACKUP_DIR%\backup_!TIMESTAMP!.sql
set BACKUP_FILE=%BACKUP_DIR%\backup.sql

echo Backing up database %DATABASE_NAME%...

:: Set PGPASSFILE environment variable to point to .pgpass file
set PGPASSFILE=C:\Users\Public\pgpass.conf

"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -h localhost -U %USER% -b -v -f "%BACKUP_FILE%" %DATABASE_NAME%

echo Backup completed.

echo Copying backup to external SSD drives...
copy "%BACKUP_FILE%" %EXTERNAL_SSD_DRIVE%
copy "%BACKUP_FILE%" %EXTERNAL2%
copy "%BACKUP_FILE%" %EXTERNAL3%
echo Copy completed.

endlocal