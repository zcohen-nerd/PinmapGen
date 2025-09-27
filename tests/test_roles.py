"""
Test cases for pin role inference functionality.
"""

import unittest
from tools.pinmapgen.roles import PinRoleInferrer


class TestRoles(unittest.TestCase):
    """Test pin role inference and bus grouping."""
    
    def test_infer_i2c_roles(self):
        """Test inference of I2C pin roles."""
        self.assertEqual(infer_pin_role("I2C0_SDA"), "i2c.sda")
        self.assertEqual(infer_pin_role("I2C_SDA"), "i2c.sda")
        self.assertEqual(infer_pin_role("SDA"), "i2c.sda")
        
        self.assertEqual(infer_pin_role("I2C0_SCL"), "i2c.scl")
        self.assertEqual(infer_pin_role("I2C_SCL"), "i2c.scl")
        self.assertEqual(infer_pin_role("SCL"), "i2c.scl")
        
    def test_infer_spi_roles(self):
        """Test inference of SPI pin roles."""
        self.assertEqual(infer_pin_role("SPI_MOSI"), "spi.mosi")
        self.assertEqual(infer_pin_role("MOSI"), "spi.mosi")
        
        self.assertEqual(infer_pin_role("SPI_MISO"), "spi.miso")
        self.assertEqual(infer_pin_role("MISO"), "spi.miso")
        
        self.assertEqual(infer_pin_role("SPI_SCK"), "spi.sck")
        self.assertEqual(infer_pin_role("SCK"), "spi.sck")
        
        self.assertEqual(infer_pin_role("SPI_CS"), "spi.cs")
        self.assertEqual(infer_pin_role("CS"), "spi.cs")
        
    def test_infer_uart_roles(self):
        """Test inference of UART pin roles."""
        self.assertEqual(infer_pin_role("UART_TX"), "uart.tx")
        self.assertEqual(infer_pin_role("TX"), "uart.tx")
        
        self.assertEqual(infer_pin_role("UART_RX"), "uart.rx")
        self.assertEqual(infer_pin_role("RX"), "uart.rx")
        
    def test_infer_pwm_roles(self):
        """Test inference of PWM pin roles."""
        self.assertEqual(infer_pin_role("PWM_OUT"), "pwm")
        self.assertEqual(infer_pin_role("MOTOR_PWM"), "pwm")
        self.assertEqual(infer_pin_role("LED_PWM"), "pwm")
        
    def test_infer_adc_roles(self):
        """Test inference of ADC pin roles."""
        self.assertEqual(infer_pin_role("ADC_IN"), "adc")
        self.assertEqual(infer_pin_role("ANALOG_IN"), "adc")
        self.assertEqual(infer_pin_role("SENSOR_A0"), "adc")
        
    def test_infer_usb_roles(self):
        """Test inference of USB pin roles."""
        self.assertEqual(infer_pin_role("USB_DP"), "usb.dp")
        self.assertEqual(infer_pin_role("USB_DM"), "usb.dm")
        self.assertEqual(infer_pin_role("USB_DN"), "usb.dm")
        
    def test_infer_can_roles(self):
        """Test inference of CAN bus pin roles."""
        self.assertEqual(infer_pin_role("CAN_H"), "can.canh")
        self.assertEqual(infer_pin_role("CANH"), "can.canh")
        
        self.assertEqual(infer_pin_role("CAN_L"), "can.canl")
        self.assertEqual(infer_pin_role("CANL"), "can.canl")
        
    def test_infer_gpio_roles(self):
        """Test inference of general GPIO roles."""
        self.assertEqual(infer_pin_role("LED"), "gpio.out")
        self.assertEqual(infer_pin_role("BUTTON"), "gpio.in")
        self.assertEqual(infer_pin_role("RELAY"), "gpio.out")
        
    def test_infer_unknown_roles(self):
        """Test handling of unknown pin names."""
        self.assertEqual(infer_pin_role("UNKNOWN_PIN"), "gpio")
        self.assertEqual(infer_pin_role(""), "gpio")
        
    def test_case_insensitive_inference(self):
        """Test that role inference is case insensitive."""
        self.assertEqual(infer_pin_role("i2c_sda"), "i2c.sda")
        self.assertEqual(infer_pin_role("Spi_Mosi"), "spi.mosi")
        self.assertEqual(infer_pin_role("pwm_out"), "pwm")
        
    def test_group_pins_by_bus(self):
        """Test grouping pins by bus functionality."""
        pin_assignments = [
            ("GP0", "I2C0_SDA"),
            ("GP1", "I2C0_SCL"),
            ("GP2", "SPI_MOSI"),
            ("GP3", "SPI_MISO"),
            ("GP4", "SPI_SCK"),
            ("GP5", "UART_TX"),
            ("GP6", "UART_RX"),
            ("GP7", "LED"),
        ]
        
        # Convert to the format expected by group_pins_by_bus
        pins_with_roles = []
        for pin, net in pin_assignments:
            role = infer_pin_role(net)
            pins_with_roles.append((pin, net, role))
        
        buses = group_pins_by_bus(pins_with_roles)
        
        # Check that buses are properly identified
        self.assertIn("I2C0", buses)
        self.assertIn("SPI", buses)
        self.assertIn("UART", buses)
        
        # Check bus contents
        i2c_bus = buses["I2C0"]
        self.assertEqual(len(i2c_bus), 2)
        spi_bus = buses["SPI"]
        self.assertEqual(len(spi_bus), 3)
        uart_bus = buses["UART"]
        self.assertEqual(len(uart_bus), 2)
        
    def test_numbered_bus_inference(self):
        """Test inference of numbered bus instances."""
        self.assertEqual(infer_pin_role("I2C1_SDA"), "i2c.sda")
        self.assertEqual(infer_pin_role("SPI2_MOSI"), "spi.mosi")
        self.assertEqual(infer_pin_role("UART3_TX"), "uart.tx")


if __name__ == "__main__":
    unittest.main()