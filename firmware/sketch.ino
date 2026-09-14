/*
 * Multi-protocol sensor node  -  ESP32
 * -----------------------------------
 * One small board talking to the outside world four different ways, which is
 * what a real instrumentation node does:
 *
 *   1-Wire  DHT22 temperature and humidity sensor on GPIO 15
 *   I2C     16x2 character LCD at address 0x27 (SDA 21, SCL 22)
 *   ADC     10 kOhm potentiometer on GPIO 34, used as the alarm set point
 *   UART    CSV telemetry at 115200 baud for the Python host program
 *
 * The firmware is deliberately non-blocking: there is no delay() in loop().
 * Every job has its own "next time to run" stamp, so the serial command
 * handler stays responsive while the sensor is being sampled.
 *
 * Serial commands (type them in the monitor and press enter)
 *   h   print help
 *   c   print the CSV header again
 *   s   print the current reading once
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "DHTesp.h"

/* ---------------- configuration ---------------- */
static const int      PIN_DHT       = 15;
static const int      PIN_POT       = 34;
static const int      PIN_LED       = 2;
static const uint8_t  LCD_ADDRESS   = 0x27;
static const uint32_t SENSOR_PERIOD = 2000;   /* ms, DHT22 needs >= 2 s */
static const uint32_t LCD_PERIOD    = 500;    /* ms */
static const float    SET_MIN       = 20.0f;  /* pot fully left  */
static const float    SET_MAX       = 40.0f;  /* pot fully right */

/* ---------------- objects and state ---------------- */
LiquidCrystal_I2C lcd(LCD_ADDRESS, 16, 2);
DHTesp dht;

static float    temperature = 0.0f;
static float    humidity    = 0.0f;
static float    setpoint    = 30.0f;
static bool     alarm       = false;
static bool     sensorOk    = false;
static uint32_t samples     = 0;

static uint32_t nextSensor = 0;
static uint32_t nextLcd    = 0;

/* Exponential moving average. A cheap low-pass filter: each new reading only
 * moves the output part of the way, so a single noisy sample cannot swing the
 * alarm. alpha = 0.3 keeps it responsive while still smoothing.            */
static float ema(float previous, float sample, float alpha)
{
    return previous + alpha * (sample - previous);
}

static void printHeader()
{
    Serial.println(F("millis,temperature_c,humidity_pct,setpoint_c,alarm"));
}

static void printSample()
{
    Serial.print(millis());       Serial.print(',');
    Serial.print(temperature, 2); Serial.print(',');
    Serial.print(humidity, 2);    Serial.print(',');
    Serial.print(setpoint, 2);    Serial.print(',');
    Serial.println(alarm ? 1 : 0);
}

static void handleSerial()
{
    while (Serial.available()) {
        char c = (char)Serial.read();
        switch (c) {
            case 'h':
                Serial.println(F("# h help | c csv header | s single sample"));
                break;
            case 'c':
                printHeader();
                break;
            case 's':
                printSample();
                break;
            default:
                break;   /* ignore newlines and anything else */
        }
    }
}

void setup()
{
    Serial.begin(115200);
    pinMode(PIN_LED, OUTPUT);

    Wire.begin();            /* I2C on the default ESP32 pins: SDA 21, SCL 22 */
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("Sensor node");
    lcd.setCursor(0, 1);
    lcd.print("starting...");

    dht.setup(PIN_DHT, DHTesp::DHT22);

    /* The ESP32 ADC is 12 bit, so readings run from 0 to 4095. */
    analogReadResolution(12);

    delay(1000);             /* the only delay in the program, during start-up */
    lcd.clear();
    printHeader();
}

void loop()
{
    uint32_t now = millis();

    handleSerial();

    /* ---- set point follows the potentiometer, read every pass ---- */
    int raw = analogRead(PIN_POT);
    setpoint = SET_MIN + (SET_MAX - SET_MIN) * (float)raw / 4095.0f;

    /* ---- sample the sensor on its own schedule ---- */
    if ((int32_t)(now - nextSensor) >= 0) {
        nextSensor = now + SENSOR_PERIOD;

        TempAndHumidity r = dht.getTempAndHumidity();
        if (dht.getStatus() == DHTesp::ERROR_NONE) {
            if (!sensorOk) {          /* first good reading seeds the filter */
                temperature = r.temperature;
                humidity    = r.humidity;
                sensorOk    = true;
            } else {
                temperature = ema(temperature, r.temperature, 0.3f);
                humidity    = ema(humidity,    r.humidity,    0.3f);
            }
            samples++;
            alarm = (temperature > setpoint);
            digitalWrite(PIN_LED, alarm ? HIGH : LOW);
            printSample();
        } else {
            Serial.print(F("# sensor error: "));
            Serial.println(dht.getStatusString());
        }
    }

    /* ---- refresh the LCD on its own schedule ---- */
    if ((int32_t)(now - nextLcd) >= 0) {
        nextLcd = now + LCD_PERIOD;

        char line[17];
        snprintf(line, sizeof(line), "T:%5.1fC H:%4.1f", temperature, humidity);
        lcd.setCursor(0, 0);
        lcd.print(line);

        snprintf(line, sizeof(line), "Set:%4.1fC %s", setpoint,
                 alarm ? "ALARM" : "  ok ");
        lcd.setCursor(0, 1);
        lcd.print(line);
    }
}
