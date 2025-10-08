#!/usr/bin/env python3
"""
Card Checker Bot - Ultra Stable Version
Pydroid 3 Optimized
"""

import re
import random
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Disable verbose logging
logging.basicConfig(
    format='%(message)s',
    level=logging.WARNING
)

# Bot Token
BOT_TOKEN = "8289053497:AAGpgzn-A4NyABz0mxlMZxcIJHM_B5_OjwQ"

# Simple BIN DATABASE
BIN_DATABASE = {
    "401795": {"bank": "Chase Bank", "country": "USA", "type": "Credit", "level": "Platinum", "status": "approved"},
    "411111": {"bank": "Visa Test", "country": "USA", "type": "Credit", "level": "Gold", "status": "approved"},
    "424242": {"bank": "Visa Test", "country": "USA", "type": "Credit", "level": "Platinum", "status": "approved"},
    "453211": {"bank": "Wells Fargo", "country": "USA", "type": "Credit", "level": "Classic", "status": "declined"},
    "455673": {"bank": "Capital One", "country": "USA", "type": "Credit", "level": "Platinum", "status": "approved"},
    "510805": {"bank": "Citibank", "country": "USA", "type": "Credit", "level": "World", "status": "approved"},
    "515462": {"bank": "Capital One", "country": "USA", "type": "Credit", "level": "Platinum", "status": "approved"},
    "555555": {"bank": "Mastercard Test", "country": "USA", "type": "Credit", "level": "World", "status": "approved"},
    "378282": {"bank": "American Express", "country": "USA", "type": "Credit", "level": "Platinum", "status": "approved"},
}

def luhn_check(card_number):
    """Luhn algorithm validation"""
    try:
        def digits_of(n):
            return [int(d) for d in str(n)]
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        return checksum % 10 == 0
    except:
        return False

def get_bin_info(bin_number):
    """Get BIN information"""
    if len(bin_number) < 6:
        return {"bank": "Unknown", "country": "International", "type": "Unknown", "level": "Standard", "status": "declined"}
    
    # Exact match
    if bin_number in BIN_DATABASE:
        return BIN_DATABASE[bin_number]
    
    # Default based on first digit
    first_digit = bin_number[0]
    if first_digit == '4':
        return {"bank": "Visa Bank", "country": "International", "type": "Credit/Debit", "level": "Standard", "status": "approved"}
    elif first_digit == '5':
        return {"bank": "Mastercard Bank", "country": "International", "type": "Credit/Debit", "level": "Standard", "status": "approved"}
    elif first_digit == '3':
        return {"bank": "American Express", "country": "International", "type": "Credit", "level": "Standard", "status": "approved"}
    elif first_digit == '6':
        return {"bank": "Discover Bank", "country": "International", "type": "Credit/Debit", "level": "Standard", "status": "approved"}
    else:
        return {"bank": "Unknown Bank", "country": "International", "type": "Unknown", "level": "Standard", "status": "declined"}

def parse_card_data(text):
    """Parse card data from text"""
    try:
        clean_text = re.sub(r'[^\d|/\s]', '', text)
        
        if '|' in clean_text:
            parts = clean_text.split('|')
        else:
            parts = clean_text.split()
        
        card_data = {'card': '', 'expiry': '', 'cvv': ''}
        
        for part in parts:
            part = part.strip()
            if re.match(r'^\d{13,19}$', part):
                card_data['card'] = part
            elif re.match(r'^\d{1,2}/\d{2,4}$', part):
                card_data['expiry'] = part
            elif re.match(r'^\d{3,4}$', part):
                card_data['cvv'] = part
        
        return card_data
    except:
        return {'card': '', 'expiry': '', 'cvv': ''}

def validate_expiry(expiry):
    """Validate card expiry"""
    if not expiry:
        return False, "No expiry"
    
    try:
        if '/' in expiry:
            month, year = expiry.split('/')
        else:
            return False, "Invalid"
        
        month = int(month.strip())
        year = year.strip()
        
        if len(year) == 2:
            year = '20' + year
        
        year = int(year)
        
        if month < 1 or month > 12:
            return False, "Invalid month"
        
        # Check expiry
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        
        expiry_date = datetime(next_year, next_month, 1) - timedelta(days=1)
        
        if datetime.now() > expiry_date:
            return False, "Expired"
        
        return True, "Valid"
        
    except:
        return False, "Invalid"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start command"""
    try:
        welcome_text = """
🃏 *CARD CHECKER*

*Commands:*
/start - Show this
/help - Help
/chk - Check card

*Format:* `card|mm/yy|cvv`
*Example:* `/chk 4111111111111111|12/25|123`
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    except:
        pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help command"""
    try:
        help_text = """
📖 *HELP*

*Check card:*
/chk card|mm/yy|cvv

*Examples:*
/chk 4111111111111111|12/25|123
.chk 5555555555554444|06/24|456
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    except:
        pass

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle check command"""
    try:
        # Get text from message
        if update.message.text.startswith(('/chk', '.chk')):
            parts = update.message.text.split(' ', 1)
            if len(parts) < 2:
                await update.message.reply_text("❌ Use: `/chk card|mm/yy|cvv`", parse_mode='Markdown')
                return
            text = parts[1]
        else:
            text = update.message.text
        
        # Parse card data
        card_data = parse_card_data(text)
        
        if not card_data['card']:
            await update.message.reply_text("❌ Invalid format!\nUse: `card|mm/yy|cvv`", parse_mode='Markdown')
            return
        
        card_number = card_data['card']
        
        # Validations
        luhn_valid = luhn_check(card_number)
        bin_info = get_bin_info(card_number[:6])
        expiry_valid, expiry_msg = validate_expiry(card_data['expiry'])
        
        # Determine status
        if not luhn_valid or not expiry_valid:
            status = "❌ DECLINED"
            message = "Invalid card" if not luhn_valid else "Card expired"
        elif bin_info['status'] == 'declined':
            status = "❌ DECLINED"
            message = "Transaction declined"
        else:
            status = "✅ APPROVED"
            message = "Transaction approved"
        
        # Build simple response
        response = f"""
💳 *CARD CHECK*

*Card:* `{card_number[:6]}******{card_number[-4:]}`
*Bank:* {bin_info['bank']}
*Country:* {bin_info['country']}
*Type:* {bin_info['type']}

*Check:* {'✅ Valid' if luhn_valid else '❌ Invalid'}
*Expiry:* {'✅ Valid' if expiry_valid else '❌ ' + expiry_msg}
*CVV:* {'✅ Provided' if card_data['cvv'] else '⚠️ Missing'}

*Result:* {status}
*Message:* {message}
        """
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text("❌ Error processing card!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    try:
        text = update.message.text.strip()
        
        if text.startswith('.chk ') or text.startswith('/chk '):
            await check_command(update, context)
        elif '|' in text and re.search(r'\d{13,19}', text):
            await check_command(update, context)
        else:
            await update.message.reply_text("❌ Use `/chk card|mm/yy|cvv`", parse_mode='Markdown')
    except:
        pass

def main():
    """Main function - Ultra stable"""
    print("🔄 Starting Bot...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Simple application creation
            app = Application.builder().token(BOT_TOKEN).build()
            
            # Add handlers
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("chk", check_command))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            print("✅ Bot Started!")
            print("🤖 Ready for commands...")
            
            # Start polling with minimal settings
            app.run_polling(
                poll_interval=1.0,
                timeout=10,
                drop_pending_updates=True
            )
            break
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {str(e)[:50]}...")
            if attempt < max_retries - 1:
                print("🔄 Retrying...")
                import time
                time.sleep(2)
            else:
                print("💥 Max retries reached. Closing.")
                break

if __name__ == "__main__":
    main()
