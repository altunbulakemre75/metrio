"""Testler gerçek logs/scraper.log dosyasına yazmasın.

utils.logger ilk get_logger çağrısında kök logger'a dosya yazıcısı ekliyor; testlerdeki
sahte hatalar ("Pipeline çöktü", "Anti-bot tetiklendi") gerçek günlük dosyasına düşüyor ve
gerçek bir arızayla karıştırılıyordu. Yapılandırmayı burada "yapıldı" sayıyoruz.
"""
import utils.logger

utils.logger._configured = True
