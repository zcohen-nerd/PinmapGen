"""
Test cases for pin role inference functionality.
"""

import unittest

from tools.pinmapgen.roles import PinRole, RoleInferencer


class TestRoles(unittest.TestCase):
    """Test pin role inference and bus grouping."""

    def setUp(self):
        """Set up test fixtures."""
        self.inferencer = RoleInferencer()

    def test_infer_i2c_roles(self):
        """Test inference of I2C pin roles."""
        result = self.inferencer.infer_role("I2C0_SDA")
        self.assertEqual(result, PinRole.I2C_SDA)

        result = self.inferencer.infer_role("I2C_SDA")
        self.assertEqual(result, PinRole.I2C_SDA)

        result = self.inferencer.infer_role("SDA")
        self.assertEqual(result, PinRole.I2C_SDA)

        result = self.inferencer.infer_role("I2C0_SCL")
        self.assertEqual(result, PinRole.I2C_SCL)

        result = self.inferencer.infer_role("I2C_SCL")
        self.assertEqual(result, PinRole.I2C_SCL)

        result = self.inferencer.infer_role("SCL")
        self.assertEqual(result, PinRole.I2C_SCL)

    def test_infer_spi_roles(self):
        """Test inference of SPI pin roles."""
        result = self.inferencer.infer_role("SPI_MOSI")
        self.assertEqual(result, PinRole.SPI_MOSI)

        result = self.inferencer.infer_role("MOSI")
        self.assertEqual(result, PinRole.SPI_MOSI)

        result = self.inferencer.infer_role("SPI_MISO")
        self.assertEqual(result, PinRole.SPI_MISO)

        result = self.inferencer.infer_role("MISO")
        self.assertEqual(result, PinRole.SPI_MISO)

        result = self.inferencer.infer_role("SPI_SCK")
        self.assertEqual(result, PinRole.SPI_SCK)

        result = self.inferencer.infer_role("SCK")
        self.assertEqual(result, PinRole.SPI_SCK)

        result = self.inferencer.infer_role("SPI_CS")
        self.assertEqual(result, PinRole.SPI_CS)

        result = self.inferencer.infer_role("CS")
        self.assertEqual(result, PinRole.SPI_CS)

    def test_infer_uart_roles(self):
        """Test inference of UART pin roles."""
        result = self.inferencer.infer_role("UART_TX")
        self.assertEqual(result, PinRole.UART_TX)

        result = self.inferencer.infer_role("TX")
        self.assertEqual(result, PinRole.UART_TX)

        result = self.inferencer.infer_role("UART_RX")
        self.assertEqual(result, PinRole.UART_RX)

        result = self.inferencer.infer_role("RX")
        self.assertEqual(result, PinRole.UART_RX)

    def test_infer_pwm_roles(self):
        """Test inference of PWM pin roles."""
        result = self.inferencer.infer_role("PWM_OUT")
        self.assertEqual(result, PinRole.PWM)

        result = self.inferencer.infer_role("MOTOR_PWM")
        self.assertEqual(result, PinRole.PWM)

        result = self.inferencer.infer_role("LED_PWM")
        self.assertEqual(result, PinRole.PWM)

    def test_infer_adc_roles(self):
        """Test inference of ADC pin roles."""
        result = self.inferencer.infer_role("ADC_IN")
        self.assertEqual(result, PinRole.ADC)

        result = self.inferencer.infer_role("ANALOG_IN")
        self.assertEqual(result, PinRole.ADC)

        # Test a name that should match ADC pattern
        result = self.inferencer.infer_role("AIN0")
        self.assertEqual(result, PinRole.ADC)

    def test_infer_usb_roles(self):
        """Test inference of USB pin roles."""
        result = self.inferencer.infer_role("USB_DP")
        self.assertEqual(result, PinRole.USB_DP)

        result = self.inferencer.infer_role("USB_DN")
        self.assertEqual(result, PinRole.USB_DN)

    def test_infer_can_roles(self):
        """Test inference of CAN bus pin roles."""
        result = self.inferencer.infer_role("CAN_H")
        self.assertEqual(result, PinRole.CAN_H)

        result = self.inferencer.infer_role("CANH")
        self.assertEqual(result, PinRole.CAN_H)

        result = self.inferencer.infer_role("CAN_L")
        self.assertEqual(result, PinRole.CAN_L)

        result = self.inferencer.infer_role("CANL")
        self.assertEqual(result, PinRole.CAN_L)

    def test_infer_gpio_roles(self):
        """Test inference of general GPIO roles."""
        result = self.inferencer.infer_role("LED")
        self.assertEqual(result, PinRole.LED)

        result = self.inferencer.infer_role("BUTTON")
        self.assertEqual(result, PinRole.BUTTON)

        result = self.inferencer.infer_role("GPIO_OUT")
        self.assertEqual(result, PinRole.GPIO_OUT)

    def test_infer_unknown_roles(self):
        """Test handling of unknown pin names."""
        # UNKNOWN_PIN contains "IN" so it triggers GPIO_IN fallback
        result = self.inferencer.infer_role("UNKNOWN_PIN")
        self.assertEqual(result, PinRole.GPIO_IN)

        # Test truly unknown net name
        result = self.inferencer.infer_role("MYSTERY_NET")
        self.assertEqual(result, PinRole.UNKNOWN)

        result = self.inferencer.infer_role("")
        self.assertEqual(result, PinRole.UNKNOWN)

    def test_case_insensitive_inference(self):
        """Test that role inference is case insensitive."""
        result = self.inferencer.infer_role("i2c_sda")
        self.assertEqual(result, PinRole.I2C_SDA)

        result = self.inferencer.infer_role("Spi_Mosi")
        self.assertEqual(result, PinRole.SPI_MOSI)

        result = self.inferencer.infer_role("pwm_out")
        self.assertEqual(result, PinRole.PWM)


if __name__ == "__main__":
    unittest.main()
