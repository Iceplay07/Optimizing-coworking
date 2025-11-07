import asyncpg
from datetime import datetime, timedelta, time
import logging
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL')

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.pool = None
        self.database_url = DATABASE_URL

    async def create_pool(self):
        try:
            self.pool = await asyncpg.create_pool(self.database_url)
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating database pool: {e}")
            raise

    async def ensure_pool(self):
        """Убедиться, что пул соединений создан"""
        if self.pool is None:
            await self.create_pool()

    def get_current_date(self):
        """Получить текущую дату"""
        return datetime.now().date()

    async def get_user(self, user_id):
        """Получить пользователя по ID"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            user = await connection.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
            logger.info(f"Database.get_user: user_id={user_id}, found={user is not None}")
            if user:
                logger.info(f"User data: {dict(user)}")
            return user

    async def get_bookings_by_date_and_type(self, booking_date, booking_type=None):
        """Получить бронирования по дате и типу (если тип не указан - все типы)"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            if booking_type and booking_type != "all":
                return await connection.fetch('''
                    SELECT b.*, u.full_name 
                    FROM bookings b
                    JOIN users u ON b.user_id = u.user_id
                    WHERE b.booking_date = $1 AND b.booking_type = $2 AND b.status = 'active'
                    ORDER BY b.start_time
                ''', booking_date, booking_type)
            else:
                return await connection.fetch('''
                    SELECT b.*, u.full_name 
                    FROM bookings b
                    JOIN users u ON b.user_id = u.user_id
                    WHERE b.booking_date = $1 AND b.status = 'active'
                    ORDER BY b.booking_type, b.start_time
                ''', booking_date)


    async def add_user(self, user_id, full_name, phone, is_student):
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            await connection.execute('''
                INSERT INTO users (user_id, full_name, phone, is_student)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                full_name = $2, phone = $3, is_student = $4
            ''', user_id, full_name, phone, is_student)

    async def add_booking(self, user_id, booking_type, booking_date, start_time, end_time):
        """Добавляет бронирование - используем объекты времени напрямую"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            try:
                logger.info(f"Adding booking: {user_id}, {booking_type}, {booking_date}, {start_time}, {end_time}")
                booking_id = await connection.fetchval('''
                    INSERT INTO bookings (user_id, booking_type, booking_date, start_time, end_time)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                ''', user_id, booking_type, booking_date, start_time, end_time)
                logger.info(f"Booking added successfully with ID: {booking_id}")
                return booking_id
            except Exception as e:
                logger.error(f"Error in add_booking: {e}")
                raise

    async def get_user_bookings(self, user_id, active_only=True):
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            if active_only:
                return await connection.fetch('''
                    SELECT * FROM bookings 
                    WHERE user_id = $1 AND status = 'active' AND booking_date >= CURRENT_DATE
                    ORDER BY booking_date, start_time
                ''', user_id)
            else:
                return await connection.fetch('''
                    SELECT * FROM bookings 
                    WHERE user_id = $1
                    ORDER BY booking_date DESC, start_time DESC
                ''', user_id)

    async def get_all_active_bookings(self):
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            return await connection.fetch('''
                SELECT u.full_name, b.booking_type, b.booking_date, b.start_time, b.end_time, b.id
                FROM bookings b
                JOIN users u ON b.user_id = u.user_id
                WHERE b.status = 'active' AND b.booking_date >= CURRENT_DATE
                ORDER BY b.booking_date, b.start_time
            ''')

    async def get_all_users(self):
        """Получить всех пользователей"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            return await connection.fetch('''
                SELECT * FROM users ORDER BY created_at DESC
            ''')

    async def get_all_bookings(self):
        """Получить все бронирования"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            return await connection.fetch('''
                SELECT b.*, u.full_name 
                FROM bookings b
                LEFT JOIN users u ON b.user_id = u.user_id
                ORDER BY b.created_at DESC
            ''')

    async def cancel_booking(self, booking_id, user_id):
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            result = await connection.execute('''
                UPDATE bookings SET status = 'cancelled'
                WHERE id = $1 AND user_id = $2 AND status = 'active'
            ''', booking_id, user_id)
            return result != 'UPDATE 0'

    async def get_booking_by_id(self, booking_id):
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            return await connection.fetchrow('''
                SELECT b.*, u.full_name 
                FROM bookings b
                JOIN users u ON b.user_id = u.user_id
                WHERE b.id = $1
            ''', booking_id)

    async def has_booking_type_on_date(self, user_id, booking_type, date):
        """Проверяет, есть ли у пользователя бронь данного типа на указанную дату"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            booking = await connection.fetchrow('''
                SELECT id FROM bookings 
                WHERE user_id = $1 
                AND booking_type = $2 
                AND booking_date = $3
                AND status = 'active'
            ''', user_id, booking_type, date)
            return booking is not None

    async def cleanup_expired_bookings(self):
        """Очищает просроченные бронирования"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            result = await connection.execute('''
                UPDATE bookings 
                SET status = 'expired' 
                WHERE (booking_date < CURRENT_DATE 
                OR (booking_date = CURRENT_DATE AND end_time < CURRENT_TIME))
                AND status = 'active'
            ''')
            logger.info(f"Expired bookings cleanup completed: {result}")
            return result

    async def get_user_active_booking_types_for_week(self, user_id, week_start_date):
        """Получает типы бронирований пользователя на указанную неделю"""
        await self.ensure_pool()
        week_end_date = week_start_date + timedelta(days=6)

        async with self.pool.acquire() as connection:
            return await connection.fetch('''
                SELECT DISTINCT booking_type, booking_date
                FROM bookings 
                WHERE user_id = $1 
                AND booking_date BETWEEN $2 AND $3
                AND status = 'active'
            ''', user_id, week_start_date, week_end_date)

    async def get_conflicting_bookings(self, booking_date, start_time, end_time, booking_type):
        """Проверяет пересекающиеся бронирования на указанное время для конкретного типа"""
        await self.ensure_pool()
        async with self.pool.acquire() as connection:
            logger.info(f"Checking conflicts for {booking_type} on {booking_date} from {start_time} to {end_time}")

            try:
                # Используем объекты времени напрямую - asyncpg умеет с ними работать
                result = await connection.fetch('''
                    SELECT b.*, u.full_name 
                    FROM bookings b
                    JOIN users u ON b.user_id = u.user_id
                    WHERE b.booking_date = $1 
                    AND b.booking_type = $2
                    AND b.status = 'active'
                    AND (
                        (b.start_time < $4 AND b.end_time > $3) OR
                        (b.start_time >= $3 AND b.start_time < $4) OR
                        (b.end_time > $3 AND b.end_time <= $4) OR
                        (b.start_time <= $3 AND b.end_time >= $4)
                    )
                ''', booking_date, booking_type, start_time, end_time)

                logger.info(f"Found {len(result)} conflicting bookings")
                return result

            except Exception as e:
                logger.error(f"Error in get_conflicting_bookings: {e}")
                return []

    async def get_booking_count_by_type_time(self, booking_date, start_time, end_time, booking_type):
        """Получает количество активных бронирований определенного типа в указанный промежуток времени"""
        await self.ensure_pool()

        async with self.pool.acquire() as connection:
            try:
                return await connection.fetchval('''
                    SELECT COUNT(*) 
                    FROM bookings 
                    WHERE booking_date = $1 
                    AND booking_type = $2
                    AND status = 'active'
                    AND (
                        (start_time < $4 AND end_time > $3) OR
                        (start_time >= $3 AND start_time < $4) OR
                        (end_time > $3 AND end_time <= $4) OR
                        (start_time <= $3 AND end_time >= $4)
                    )
                ''', booking_date, booking_type, start_time, end_time)
            except Exception as e:
                logger.error(f"Error in get_booking_count_by_type_time: {e}")
                return 0